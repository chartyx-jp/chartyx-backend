# apps/users/services.py
from apps.users.models import Member
from django.core.exceptions import ObjectDoesNotExist

class UserManager:
    @staticmethod
    def create_member(data):
        member = Member.objects.create(**data)
        return member

    @staticmethod
    def get_member_by_email_and_password(email, hashed_password):
        try:
            return Member.objects.get(emailAddress=email, password=hashed_password)
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def update_member(user_id, update_data):
        try:
            member = Member.objects.get(id=user_id)
            for key, value in update_data.items():
                setattr(member, key, value)
            member.save()
            return member
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def delete_member(user_id, email):
        try:
            member = Member.objects.get(id=user_id, emailAddress=email)
            member.delete()
            return True
        except ObjectDoesNotExist:
            return False
