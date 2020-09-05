# OpenStack Course Manager

## Installation


**Step 1:** Perform basic installation:
```
cd /var/www
git clone https://github.com/pr0fg/openstack-course-manager
cd /var/www/openstack-course-manager
export PIPENV_VENV_IN_PROJECT="enabled"
pipenv --three install
```

**Step 2:** Edit configuration items in `config.py` or create a `.env` file, as needed.

**Step 3:** Modify `app.wsgi` file and change paths (if needed).

**Step 4:** Install Apache2 WSGI Directive
Edit `/etc/apache2/conf-available/openstack-dashboard.conf` and include the following:
```
WSGIDaemonProcess oscm user=www-data group=www-data processes=1 threads=2 display-name=%{GROUP}
WSGIScriptAlias /api /var/www/openstack-course-manager/app.wsgi process-group=oscm

<Directory "/var/www/openstack-course-manager">
    WSGIProcessGroup oscm
    WSGIApplicationGroup %{GLOBAL}
    WSGIPassAuthorization On
    WSGIScriptReloading On
    Require all granted
</Directory>

Alias /manage /var/www/openstack-course-manager/www
<Directory "/var/www/openstack-course-manager/www">
    DirectoryIndex login.html
    Options -Indexes
    AllowOverride None
</Directory>
<Directory "/var/www/openstack-course-manager/www/templates">
    Require all denied
</Directory>
```

**Step 5:** Prepare RabbitMQ
```
rabbitmqctl add_vhost oscm
rabbitmqctl add_user oscm password
rabbitmqctl set_permissions -p oscm oscm ".*" ".*" ".*"
```

**Step 6:** Register Celery Worker Under systemd
Edit `/etc/systemd/system/oscm.service` with the following:
```
[Unit]
Description=OpenStack Course Manager Celery Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/openstack-course-manager
ExecStart=/var/www/openstack-course-manager/.venv/bin/celery worker -A api.celery -B -s /var/www/openstack-course-manager/.celerybeat-schedule --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```
Reload systemd and start the service by doing `systemctl daemon-reload` then `systemctl start oscm`.


**Step 7:** Integrate Password Reset with OpenStack Horizon
To integrate the password reset functionality with OpenStack horizon's login page, copy `openstack_dashboard/templates/_login_footer.html` to your OpenStack horizon template folder (likely `/usr/share/openstack-dashboard/openstack_dashboard/templates/`). 

Restart `apache2` and `memcached` to push through the change. You should see the password reset button show up on the login page.


**Step 8:** Finalize Installation
```
chown -R www-data:www-data /var/www/openstack-course-manager
systemctl restart apache2
```

## Configuration

Edit `config.py` and configure your settings accordingly. Note that most sensitive variables are imported as environmental variables. I highly recommend using this method for security and scalability reasons.

## Usage

You must load all relevant environmental variables prior to using this software (including the `openrc` configuration for a cloud admin user). Check out `config.py` for a full list.


### Running the Celery Worker

Add/edit any settings in `.env`, then do:

```
celery worker -A api.celery -n 'worker-1' -B -s /tmp/celerybeat-schedule --loglevel=info
```

You should probably register this as a system service...


### Web Assets

This web panel is designed to integrate with the OpenStack Course Manager's API system. All paths are relative, so you should be able to use this on any domain as long as the API endpoint is on the same domain under `/api`.

You can generate static assets by modifying the Jinja2 templates under `www/templates`. Then simply run `staticjinja build` to generate the new assets.


## Running the API Server (Development)

Add/edit any settings in `.env` and `.flaskenv` (i.e. `FLASK_DEBUG`, `FLASK_RUN_HOST`, and `FLASK_RUN_PORT`), then do:

```
flask run
```

Note that if `DEBUG=1` and `WWW_ROOT` are set as environmental variables, flask will also serve out `www` under `/` (for development purposes).

## Debug Mode

Debug mode for this software can be enabled by exporting the environmental variable `DEBUG=1`. 

Don't forget, you can run a development SMTP server by doing `python -m smtpd -n -c DebuggingServer dev-localhost:2525`.


## Running Tests

A significant amount of this code base can be tested automatically using `pytest` via `tests/test_manager.py`. 

***Don't forget to load OpenStack environmental variables prior to testing!***

To test all covered functionality, simply do `pytest --log-cli-level=10 --disable-pytest-warnings test_oscm.py`.
