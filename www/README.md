# OpenStack Course Manager - Web Panel


## Description
This web panel is designed to integrate with the OpenStack Course Manager's API system. All paths are relative, so you should be able to use this on any domain as long as the API endpoint is on the same domain under `/api`.

## Installation
```
pipenv --three install
pipenv shell
```

## Build Site

You can build the site's files by simply doing: 

```
staticjinja build
```

## Debug Mode

```
staticjinja watch
```