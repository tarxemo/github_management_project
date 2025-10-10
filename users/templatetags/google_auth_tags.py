from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def google_one_tap():
    if not getattr(settings, 'GOOGLE_OAUTH2_CLIENT_ID', None):
        return ''
    
    client_id = settings.GOOGLE_OAUTH2_CLIENT_ID
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    
    return mark_safe(f"""
    <script src="https://accounts.google.com/gsi/client" async defer></script>
    <div id="g_id_onload"
         data-client_id="{client_id}"
         data-context="signin"
         data-ux_mode="popup"
         data-login_uri="{site_url}/accounts/google/onetap/"
         data-auto_prompt="true"
         data-callback="handleCredentialResponse"
         data-itp_support="true"
         data-auto_select="true">
    </div>
    
    <div id="g_id_signin"></div>
    
    <script>
    function handleCredentialResponse(response) {{
        const csrftoken = getCsrfToken();
        if (!csrftoken) {{
            console.error('CSRF token not found');
            return;
        }}
        
        fetch('{site_url}/accounts/google/onetap/', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrftoken,
                'X-Requested-With': 'XMLHttpRequest'
            }},
            body: 'credential=' + encodeURIComponent(response.credential),
            credentials: 'same-origin'
        }})
        .then(response => {{
            if (response.redirected) {{
                window.location.href = response.url;
                return;
            }}
            return response.json().then(data => {{
                if (data.success && data.redirect) {{
                    window.location.href = data.redirect;
                }} else if (data.error) {{
                    console.error('Authentication failed:', data.error);
                }} else {{
                    window.location.reload();
                }}
            }});
        }})
        .catch(error => {{
            console.error('Error:', error);
        }});
    }}
    
    function getCsrfToken() {{
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }}
    
    // Initialize Google One Tap
    window.onload = function() {{
        if (typeof google === 'undefined' || !google.accounts) {{
            console.error('Google Identity Services API not loaded');
            return;
        }}
        
        google.accounts.id.initialize({{
            client_id: '{client_id}',
            callback: handleCredentialResponse,
            context: 'signin',
            ux_mode: 'popup',
            auto_select: true
        }});
        
        // Try to show the One Tap prompt
        google.accounts.id.prompt(notification => {{
            if (notification.isNotDisplayed()) {{
                const reason = notification.getNotDisplayedReason();
                console.log('One Tap prompt was not shown. Reason:', reason);
                
                // Show fallback button if needed
                if (reason === 'user_cancel' || reason === 'browser_not_supported') {{
                    console.log('Showing fallback button');
                    google.accounts.id.renderButton(
                        document.getElementById('g_id_signin'),
                        {{ 
                            type: 'standard',
                            theme: 'outline',
                            size: 'large',
                            width: 240,
                            text: 'signin_with'
                        }}
                    );
                }}
            }}
        }});
    }};
    </script>
    
    <style>
    #g_id_onload {{
        position: fixed;
        top: 1rem;
        right: 1rem;
        z-index: 1000;
        display: none;
    }}
    
    #g_id_signin {{
        position: fixed;
        top: 1rem;
        right: 1rem;
        z-index: 1000;
    }}
    </style>
    """)