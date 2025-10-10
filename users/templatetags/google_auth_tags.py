from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def google_one_tap():
    if not getattr(settings, 'GOOGLE_OAUTH2_CLIENT_ID', None):
        return ''
    
    client_id = settings.GOOGLE_OAUTH2_CLIENT_ID
    site_url = getattr(settings, 'SITE_URL', '')
    
    return mark_safe("""
    <script src="https://accounts.google.com/gsi/client" async defer></script>
    <div id="g_id_onload"
         data-client_id="%s"
         data-context="signin"
         data-ux_mode="popup"
         data-login_uri="%s/accounts/google/onetap/"
         data-auto_prompt="true"
         data-callback="handleCredentialResponse"
         data-itp_support="true"
         data-auto_select="true">
    </div>
    
    <div id="g_id_signin"></div>
    
    <script>
    function handleCredentialResponse(response) {
        const getCookie = (name) => {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        };
        
        const csrftoken = getCookie('csrftoken');
        const siteUrl = '%s';
        
        fetch(siteUrl + '/accounts/google/onetap/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrftoken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: 'credential=' + encodeURIComponent(response.credential),
            credentials: 'same-origin'
        })
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }
            return response.json().then(data => {
                if (data.success && data.redirect) {
                    window.location.href = data.redirect;
                } else if (data.error) {
                    console.error('Authentication failed:', data.error);
                } else {
                    window.location.reload();
                }
            });
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
    
    // Load Google Identity Services API
    function loadGoogleIdentityServices() {
        if (typeof google !== 'undefined' && google.accounts) {
            initializeGoogleOneTap();
        } else {
            // If Google API isn't loaded yet, wait for it
            window.addEventListener('load', initializeGoogleOneTap);
        }
    }

    function initializeGoogleOneTap() {
        if (typeof google === 'undefined' || !google.accounts) {
            console.error('Google Identity Services API not loaded');
            return;
        }
        
        try {
            google.accounts.id.initialize({
                client_id: '%s',
                callback: handleCredentialResponse,
                context: 'signin',
                ux_mode: 'popup',
                auto_select: true,
                itp_support: true
            });
            
            // Try to display the One Tap prompt
            google.accounts.id.prompt(notification => {
                if (notification.isNotDisplayed()) {
                    const reason = notification.getNotDisplayedReason();
                    console.log('One Tap prompt was not shown. Reason:', reason);
                    
                    // If blocked by user, show the button
                    if (reason === 'user_cancel' || reason === 'browser_not_supported') {
                        console.log('Showing fallback button');
                        google.accounts.id.renderButton(
                            document.getElementById('g_id_signin'),
                            { 
                                type: 'standard',
                                theme: 'outline',
                                size: 'large',
                                width: 240,
                                text: 'signin_with',
                                shape: 'rectangular',
                                logo_alignment: 'left',
                                context: 'signin',
                                ux_mode: 'popup'
                            }
                        );
                    }
                } else if (notification.isSkippedMoment() || notification.isDismissedMoment()) {
                    console.log('One Tap prompt was skipped or dismissed');
                }
            });
        } catch (error) {
            console.error('Error initializing Google One Tap:', error);
        }
    }
    
    // Start the process when the page loads
    document.addEventListener('DOMContentLoaded', loadGoogleIdentityServices);
    </script>
    
    <style>
    #g_id_onload {
        position: fixed;
        top: 1rem;
        right: 1rem;
        z-index: 1000;
        display: none;
    }
    
    #g_id_signin {
        position: fixed;
        top: 1rem;
        right: 1rem;
        z-index: 1000;
    }
    </style>
    """ % (client_id, site_url, site_url, client_id))
