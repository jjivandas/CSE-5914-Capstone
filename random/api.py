import requests
response = requests.get('https://api-web.nhle.com/v1/schedule/now')
print(response.json())