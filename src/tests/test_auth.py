auth_prefix = f"/api/v1/auth"


def test_user_creation(fake_session, fake_user_service, test_client):

    signup_data = {
        "username": "AhmadMajdi",
        "email": "ahmadbara58@gmail.com",
        "password": "TestPass123!",
        "first_name": "Ahmad",
        "last_name": "Majdi",
    }
    response = test_client.post(url=f"{auth_prefix}/signup", json=signup_data)

    fake_user_service.user_exists.assert_called_once()

    fake_user_service.user_exists.assert_called_once_with(
        signup_data["email"], fake_session
    )

    fake_user_service.create_user.assert_called_once()

    user_data_arg, session_arg = fake_user_service.create_user.call_args.args
    assert user_data_arg.email == signup_data["email"]
    assert session_arg is fake_session
