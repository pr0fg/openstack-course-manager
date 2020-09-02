# OpenStack Course Manager

## Installation
```
pipenv --three install
pipenv shell
```

## Configuration

Edit `config.py` and configure your settings accordingly. Note that most sensitive variables are imported as environmental variables. I highly recommend using this method for security and scalability reasons.

## Usage

You must load all relevant environmental variables prior to using this software (including the `openrc` configuration for a cloud admin user). Check out `config.py` for a full list.


### Running the API Server

Add/edit any settings in `.env` and `.flaskenv` (i.e. `FLASK_DEBUG`, `FLASK_RUN_HOST`, and `FLASK_RUN_PORT`), then do:

```
flask run
```

Note that if `DEBUG=1` and `WWW_ROOT` are set as environmental variables, flask will also serve out `www` under `/` (for development purposes).


### Running the Celery Worker

Add/edit any settings in `.env`, then do:

```
celery worker -A api.celery -n 'worker-1' --loglevel=info
```

You should probably register this as a system service...


### Web Assets

This web panel is designed to integrate with the OpenStack Course Manager's API system. All paths are relative, so you should be able to use this on any domain as long as the API endpoint is on the same domain under `/api`.

You can generate static assets by modifying the Jinja2 templates under `www/templates`. Then simply run `staticjinja build` to generate the new assets.


## Debug Mode

Debug mode for this software can be enabled by exporting the environmental variable `DEBUG=1`. 

Don't forget, you can run a development SMTP server by doing `python -m smtpd -n -c DebuggingServer dev-localhost:2525`.


## Running Tests

A significant amount of this code base can be tested automatically using `pytest` via `tests/test_manager.py`. 

***Don't forget to load OpenStack environmental variables prior to testing!***

To test all covered functionality, simply do `pytest --log-cli-level=10 --disable-pytest-warnings test_oscm.py`.
