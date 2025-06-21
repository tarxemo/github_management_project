# RB
```
from your_app.models import User, ChickenHouse

for user in User.objects.all():
    if user.chicken_house:
        user.chicken_house.owner = user
        user.chicken_house.save()
```