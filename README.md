## Keyence Web Dashboard Information Scrape
This project allows you to access various Keyence Printer Dashboards and scrapes essential information such as the Ink Level, Solvent Level, Printer Name, etc.

### Running the Application
In order to run the app, make sure you are in the project directory then run the following command in your terminal.
```
uvicorn printer_api:app --app-dir . --host 0.0.0.0 --port 5055
```

### Installing Requirements
Make sure you are in your appropriate working directory, and run the following command in your terminal.
```
pip install -r requirements.txt
```

### Important Values to Change
In the `printer_api.py` file, you need to change values in order for this to run for you.

```py
WEB_TARGETS = [
    {
        "url": "http://127.0.0.1/html/home.html",
        "username": "USERNAME",
        "password": "PASSWORD",
    }
]
```

Change the value of `url` to be the URL you use to access the main page for your Keyence Printers. Include `home.html` and any other information appended to the URL. The page should look similar to the following image.
![](https://i.imgur.com/BwjMJcq.png)

`username` and `password` should be changed to whatever you use to access that specific webpage.

You can also incorporate multiple web dashboards using this script, simply add additional blocks like the following:
```py

WEB_TARGETS = [
    {
        "url": "http://127.0.0.1/home.html?lang=en&version=02.08.02",
        "username": "USERNAME",
        "password": "PASSWORD",
    },
    {
        "url": "http://127.0.0.1/home.html?lang=en&version=02.08.02",
        "username": "USERNAME1",
        "password": "PASSWORD2",
    }
]
```