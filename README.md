All credentials are fake, and are merely examples.

A module to scrape and parse LinkedIn. LinkedinCrawler handles the web scraping, and LinkedinParser extracts relevant information from the returned HTML. 

The crawler is initiated using
```{python}
crawler = LinkedinCrawler.crawler(username=USERNAME, password=PASSWORD)
```
and logs in to LinkedIn using the provided credentials through Selenium. It is important to not run afoul of LinkedIn's web scraping policies / bot detection, so whenever possible efforts are made to mimic human behavior, e.g. random waits, staccato typing, random mistakes, scrolling up and down, etc.