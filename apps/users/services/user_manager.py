# apps/users/services.py
from apps.users.models import Member
import hashlib, time, secrets, string, datetime
from django.core.exceptions import ObjectDoesNotExist
from typing import Optional, Dict, Any

class UserManager:
    @staticmethod
    def create_member(data: Dict[str, Any]) -> Member:
        """
        データベースに新しいメンバーを作成します。

        Args:
            data (Dict[str, Any]): 新しいメンバーのデータを含む辞書。

        Returns:
            Member: 新しく作成されたMemberオブジェクト。
        """
        member = Member.objects.create(**data)
        return member


    @staticmethod
    def get_member_by_id(user_id: int) -> Optional[Member]:
        """
        メンバーIDに基づいてメンバーを取得します。

        Args:
            user_id (int): メンバーのID。

        Returns:
            Optional[Member]: 見つかった場合はMemberオブジェクト、それ以外の場合はNone。
        """
        try:
            return Member.objects.get(id=user_id)
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def get_member_by_email_and_password(email: str, hashed_password: str) -> Optional[Member]:
        """
        メールアドレスとハッシュ化されたパスワードに基づいてメンバーを取得します。

        Args:
            email (str): メンバーのメールアドレス。
            hashed_password (str): メンバーのハッシュ化されたパスワード。

        Returns:
            Optional[Member]: 見つかった場合はMemberオブジェクト、それ以外の場合はNone。
        """
        try:
            return Member.objects.get(emailAddress=email, password=hashed_password)
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def update_member(user_id: int, update_data: Dict[str, Any]) -> Optional[Member]:
        """
        既存のメンバーの情報を更新します。

        Args:
            user_id (int): 更新するメンバーのID。
            update_data (Dict[str, Any]): 更新するフィールドと新しい値を含む辞書。

        Returns:
            Optional[Member]: 見つかった場合は更新されたMemberオブジェクト、それ以外の場合はNone。
        """
        try:
            member = Member.objects.get(id=user_id)
            for key, value in update_data.items():
                setattr(member, key, value)
            member.save()
            return member
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def delete_member(user_id: int, email: str) -> bool:
        """
        データベースからメンバーを削除します。

        Args:
            user_id (int): 削除するメンバーのID。
            email (str): 削除を確認するためのメンバーのメールアドレス。

        Returns:
            bool: メンバーが正常に削除された場合はTrue、それ以外の場合はFalse。
        """
        try:
            member = Member.objects.get(id=user_id, emailAddress=email)
            member.delete()
            return True
        except ObjectDoesNotExist:
            return False

    @staticmethod
    def search_member_by_email(email: str) -> Optional[Member]:
        """
        メールアドレスでメンバーを検索します。

        Args:
            email (str): 検索するメンバーのメールアドレス。

        Returns:
            Optional[Member]: 見つかった場合はMemberオブジェクト、それ以外の場合はNone。
        """
        try:
            return Member.objects.get(emailAddress=email)
        except ObjectDoesNotExist:
            return None
        
        
    @staticmethod
    def format_required_member_data(data: Dict[str, Any]) -> Dict[str, Optional[Any]]:
        """
        提供されたデータから、メンバー（ユーザー）の必須項目を抽出し整形します。
        パスワードは自動でハッシュ化します。

        Args:
            data (Dict[str, Any]): メンバーデータを含む辞書。

        Returns:
            Dict[str, Optional[Any]]: 必須項目とそれに対応する値を含む辞書。
        """
        member_fields = [field.name for field in Member._meta.fields]
        return {
            k: UserManager._generate_hash_password(data.get(k)) if k == "password" and data.get(k) is not None else data.get(k)
            for k in member_fields
        }
        
    @staticmethod
    def _generate_hash_password(password:str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
