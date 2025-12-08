from app.core.security import create_access_token, decode_token

token = create_access_token({'sub': 'test-user-frontend', 'type': 'access'})
print('TOKEN:', token)
print('DECODED:', decode_token(token))
