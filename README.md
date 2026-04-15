# 🚀 GitHub Management & Developer Hub

Transform your GitHub journey into an engaging experience. This platform isn't just a management tool—it's a social and gamified ecosystem designed to help developers showcase their growth, compete with peers, and discover new opportunities.

---

## 🌟 Key Features

### 🏆 Unlock Achievements
Get recognized for your hard work! Whether you're a "Star Magnet," a "Commit Machine," or a "Polyglot Programmer," our achievement system tracks your milestones across multiple tiers.
- **Tiers**: Progress from Bronze to legendary Gold ranks.
- **Showcase**: Display your hard-earned badges on your profile.

### 📊 Competitive Leaderboards
See where you stand in the developer community. Our **Intelligence Score** algorithm ranks users fairly based on activity, impact, and influence.
- **Global & Regional**: Compete globally or be the #1 in your country.
- **Tech-Specific**: Find out if you're the top React developer in your region.

### 🔍 Discovery & Matching
Stop searching, start finding.
- **Discovery Feed**: Get personalized recommendations for developers and trending repositories.
- **Developer Match**: Connect with collaborators having complementary skills for your next project.

### 📈 Personal Growth Analytics
Watch your influence grow with daily snapshots of your progress.
- **Trends**: Track followers, stars, and contribution streaks.
- **Visual Insights**: Interactive charts showing your growth velocity.

---

## 📖 User Guide & Use Cases

### 1. Setting up your Profile
To get the most out of the system, you first need to sync your GitHub data:
- **Step 1**: Sign in using your GitHub account.
- **Step 2**: Go to your **Profile** page.
- **Step 3**: Click on "Sync GitHub Data" (or wait for the automatic daily sync) to fetch your repositories, stars, and languages.

### 2. Showcase Badges & Trophies
Showcase your skills and achievements directly on your GitHub profile or personal website. We offer high-fidelity SVG badges that update in real-time as your stats grow.

#### Available Badge Types
Using user **`tarxemo`** as an example, here are the available badge configurations:

| Badge Type | Description | Live Preview | Markdown Example |
| :--- | :--- | :--- | :--- |
| **🏆 Trophies** | A premium card featuring your highest-ranked achievements. | ![](https://github.tarxemo.com/badges/tarxemo/trophies/) | `![](https://github.tarxemo.com/badges/tarxemo/trophies/)` |
| **📊 Stats** | Standard metrics: Followers, Repos, and Contributions. | ![](https://github.tarxemo.com/badges/tarxemo/stats/) | `![](https://github.tarxemo.com/badges/tarxemo/stats/)` |
| **🌍 Rank** | Your current Global and Regional (Country) ranking. | ![](https://github.tarxemo.com/badges/tarxemo/rank/) | `![](https://github.tarxemo.com/badges/tarxemo/rank/)` |
| **🚀 Impact** | A weighted score showing your influence in the community. | ![](https://github.tarxemo.com/badges/tarxemo/impact/) | `![](https://github.tarxemo.com/badges/tarxemo/impact/)` |
| **💻 Languages** | Visual breakdown of your top 5 programming languages. | ![](https://github.tarxemo.com/badges/tarxemo/langs/) | `![](https://github.tarxemo.com/badges/tarxemo/langs/)` |
| **🔥 Streak** | Your longest and current contribution streaks. | ![](https://github.tarxemo.com/badges/tarxemo/streak/) | `![](https://github.tarxemo.com/badges/tarxemo/streak/)` |
| **🏅 Country Top** | Your percentile ranking within your specific country. | ![](https://github.tarxemo.com/badges/tarxemo/country-top/) | `![](https://github.tarxemo.com/badges/tarxemo/country-top/)` |

#### How to use them on your GitHub README:
Copy and paste the following snippet into your `README.md` and replace `tarxemo` with your username:

```markdown
<!-- Trophies (Large) -->
[![GitHub Trophies](https://github.tarxemo.com/badges/tarxemo/trophies/)](https://github.tarxemo.com/github/user/tarxemo/)

<!-- Stats (Small) -->
[![GitHub Stats](https://github.tarxemo.com/badges/tarxemo/stats/)](https://github.tarxemo.com/github/user/tarxemo/)
```

### 3. Climbing the Leaderboard
Want to reach the top? The system calculates your **Intelligence Score** based on:
- **Activity**: Recent commits and pull requests.
- **Impact**: Total stars and forks on your repositories.
- **Influence**: Your follower count and organization associations.
Check the [Leaderboard](https://github.tarxemo.com/github/leaderboard/) daily to see your new rank!

### 4. Discovering Collaborators
Looking for someone to help with a Python project?
- Go to the **Discovery** feed.
- Look at the "Recommended Developers" section.
- Click "Match" on a profile to see your compatibility score based on shared languages and interests.

---

## 🚀 Getting Started (Deployment)

### 🛠️ Local Development Setup

1.  **Clone & Install**:
    ```bash
    git clone <repository-url>
    pip install -r requirements.txt
    ```
2.  **Environment**: Create a `.env` file with your `GITHUB_TOKEN` and database credentials.
3.  **Migrate & Run**:
    ```bash
    python manage.py migrate
    python manage.py runserver 9000
    ```
4.  **Celery Workers**:
    ```bash
    # Run in separate terminals
    celery -A github_management_project worker -l info
    celery -A github_management_project beat -l info
    ```

---

## 📄 License
This project is licensed under the MIT License.

---

## 🙏 Join the community
Join us in building the ultimate developer ecosystem!
Project Link: [https://github.tarxemo.com](https://github.tarxemo.com)

# working versions
```
django-graphql-jwt==0.3.0 
PyJWT==1.7.1
```
