Basic readme for version 0.1

1)
You'll want to run
	pip install pydns
And pray that it works.

2.1)
You'll want to run:
	python make_password.py mypass
Where "mypass" is your email password. This will give you ascii numbers to put into the settings.conf file.
2.2)
You'll want to edit settings.conf and dns-list.txt (or other) to your liking

3)
You'll want to run:
	python dns-track.py
To start tracking the domains. Maybe you want to daemonize this using byobu/tmux

4)
You'll want to stick emailer.py as a cron job (maybe hourly or whatever)
It will email you if there have been changes.

Other notes:
setup.py was created but not worked on/tested. Probably it can be deleted.
I used dns-tracker.py which I found through a google search of how to track diffs on dns domains.
Check it out https://pleasefeedthegeek.wordpress.com/2010/08/02/dns-tracking-with-python/
Hopefully it works well, I don't know, I didn't test it much.

So as a disclaimer: I haven't tested things, I haven't optimised things, this is just an initial hack. It is, as such, quite hacky. Enjoy ;)
