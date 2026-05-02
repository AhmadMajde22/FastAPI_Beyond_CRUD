books_prefix = "/api/v1/books"


def test_get_all_books(fake_session, fake_book_service, test_client):
    fake_book_service.get_all_books.return_value = []

    test_client.get(f"{books_prefix}/")

    fake_book_service.get_all_books.assert_called_once()

    fake_book_service.get_all_books.assert_called_once_with(fake_session)
