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


Simply source them or place them in `.env`, then do: 

```
import oscm

manager = OpenStackCourseManager()

manager.add_course('INFR-1234')
manager.add_student('100123456', 'example@test.com')
manager.add_student('joe.blow', 'joe.blow@test.com')

[...]
```

## Debug Modes

Debug mode for this software can also be enabled by exporting the environmental variable `OS_DEBUG=1`. 

## Running Tests

A significant amount of this code base can be tested automatically using `pytest` via `tests/test_oscm.py`. 

***Don't forget to load OpenStack environmental variables prior to testing!***

To test all covered functionality, simply do `pytest --log-cli-level=10 --disable-pytest-warnings test_oscm.py`.
