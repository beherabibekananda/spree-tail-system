from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.groups.models import Group, GroupMembership
from datetime import datetime

class Command(BaseCommand):
    help = "Seeds the database with standard Spreetail flatmates and default group."

    def handle(self, *args, **options):
        # 1. Create standard flatmates
        flatmates = [
            {"username": "aisha", "first_name": "Aisha", "email": "aisha@example.com"},
            {"username": "rohan", "first_name": "Rohan", "email": "rohan@example.com"},
            {"username": "priya", "first_name": "Priya", "email": "priya@example.com"},
            {"username": "meera", "first_name": "Meera", "email": "meera@example.com"},
            {"username": "sam", "first_name": "Sam", "email": "sam@example.com"},
            {"username": "dev", "first_name": "Dev", "email": "dev@example.com"}
        ]
        
        users = {}
        for fm in flatmates:
            user, created = User.objects.get_or_create(
                username=fm["username"],
                defaults={
                    "email": fm["email"],
                    "first_name": fm["first_name"]
                }
            )
            if created:
                user.set_password("password123")
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created user: {user.username}"))
            else:
                self.stdout.write(f"User {user.username} already exists.")
            users[fm["username"]] = user

        # 2. Create Flat 22B Group
        group, created = Group.objects.get_or_create(
            name="Flat 22B",
            defaults={
                "description": "Shared household group for flatmates",
                "created_by": users["aisha"]
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created group: {group.name}"))
        else:
            self.stdout.write(f"Group {group.name} already exists.")

        # 3. Create memberships with exact date tracking
        # Aisha: Feb -> present
        # Rohan: Feb -> present
        # Priya: Feb -> present
        # Meera: Feb -> end of March (moved out)
        # Sam: Mid-April -> present (moved in)
        # Dev: Joined for trip (Feb onwards)
        
        memberships = [
            {"username": "aisha", "joined_at": "2024-02-01", "left_at": None},
            {"username": "rohan", "joined_at": "2024-02-01", "left_at": None},
            {"username": "priya", "joined_at": "2024-02-01", "left_at": None},
            {"username": "meera", "joined_at": "2024-02-01", "left_at": "2024-03-31"},
            {"username": "sam", "joined_at": "2024-04-15", "left_at": None},
            {"username": "dev", "joined_at": "2024-02-01", "left_at": None}
        ]

        for m in memberships:
            user = users[m["username"]]
            joined_date = datetime.strptime(m["joined_at"], "%Y-%m-%d").date()
            left_date = datetime.strptime(m["left_at"], "%Y-%m-%d").date() if m["left_at"] else None
            
            member_obj, m_created = GroupMembership.objects.get_or_create(
                user=user,
                group=group,
                defaults={
                    "joined_at": joined_date,
                    "left_at": left_date
                }
            )
            
            if m_created:
                self.stdout.write(self.style.SUCCESS(f"Added {user.username} to {group.name}"))
            else:
                # Update dates just in case
                member_obj.joined_at = joined_date
                member_obj.left_at = left_date
                member_obj.save()
                self.stdout.write(f"Updated membership for {user.username}")
                
        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
