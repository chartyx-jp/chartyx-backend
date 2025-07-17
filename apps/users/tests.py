from django.test import TestCase
from apps.common.app_initializer import DjangoAppInitializer as initializer
# Create your tests here.
initializer.setup_django()

from django.conf import settings
import smtplib

from django.test import TestCase
from apps.users.models import Member
from apps.users.services.user_manager import UserManager  # search_member_by_email をここに実装している場合
from typing import Optional

class MemberSearchTestCase(TestCase):
    def setUp(self):
        """
        テスト用メンバーを作成します。
        """
        self.email = "test@example.com"
        self.member = Member.objects.create(
            firstName="Test",
            lastName="User",
            emailAddress=self.email,
            password="dummy_hash"
        )

    def test_search_member_by_email_found(self):
        """
        メールアドレスで既存メンバーが正しく取得できるかテストします。
        """
        found_member: Optional[Member] = UserManager.search_member_by_email(self.email)
        self.assertIsNotNone(found_member)
        self.assertEqual(found_member.emailAddress, self.email)
        self.assertEqual(found_member.firstName, "Test")
        print(f"Found member: {found_member.firstName} {found_member.lastName}")

    def test_search_member_by_email_not_found(self):
        """
        存在しないメールアドレスの場合、Noneが返るかテストします。
        """
        found_member = UserManager.search_member_by_email("notfound@example.com")
        self.assertIsNone(found_member)
        

def search_member_by_email(email: str) -> Optional[Member]:
    """
    メールアドレスでメンバーを検索します。
    
    Args:
        email (str): 検索するメールアドレス。
    
    Returns:
        Optional[Member]: 見つかった場合はMemberオブジェクト、それ以外の場合はNone。
    """
    try:
        return Member.objects.get(emailAddress=email)
    except Member.DoesNotExist:
        return None


def test_send_email():
    """
    Djangoのメール送信設定が正しく機能するかを確認するテスト関数。
    """
    try:
        mail_address = "k.and.k204@gmail.com"
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(settings.DEFAULT_FROM_EMAIL, settings.EMAIL_HOST_PASSWORD)
        server.sendmail(settings.DEFAULT_FROM_EMAIL, mail_address, 'Subject:Test\n\nHello')
        server.quit()
        print("メール送信成功")
    except Exception as e:
        print(f"メール送信失敗: {e}")
        
if __name__ == "__main__":
    # test_send_email()
    print(search_member_by_email("k.and.k204@gmail.com"))
    pass
