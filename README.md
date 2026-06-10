## Keyence Webscrape Project
This project allows you to access various Keyence Printer Dashboards and scrapes essential information such as the Ink Level, Solvent Level, Printer Name, etc.


## Intructions

### Installing Requirements
Make sure you are in your appropriate working directory, and run the following command in your terminal.
```
pip install -r requirements.txt
```

### Values to Change
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

### Running the Application
In order to run the app, make sure you are in the project directory then run the following command in your terminal.
```
uvicorn printer_api:app --app-dir . --host 0.0.0.0 --port 5055
```


### Created Endpoints
Access it via whatever you are serving the data as far as the URL. By default you can use `http://127.0.0.1` if you have not routed a domain name to it.
```
/api/health
/api/printer-data
/api/printer-data/refresh
/api/printer-data.js
```


## Examples
See examples of how you would render the data.

### Website Fetch
```
async function loadPrinterData() {
    const response = await fetch("http://127.0.0.1/api/printer-data");
    const payload = await response.json();

    console.log("Last Scraped:", payload.ScrapedAt);
    console.log("Printer Count:", payload.Count);
    console.table(payload.Data);

    return payload.Data;
}

loadPrinterData();
```

### Script Include Style Page
```
<script src="http://127.0.0.1/api/printer-data.js"></script>
<script>
    console.table(printerData);
</script>
```