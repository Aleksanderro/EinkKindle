from server.main import main


def test_application_entry_point() -> None:
    assert main() is None
