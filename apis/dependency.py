from fastapi import Request


def get_app_state(request: Request):
    """
    Helper function to retrieve the application state from the request.
    """
    return request.app.state
