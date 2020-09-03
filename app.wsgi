import sys
sys.path.insert(0, '/var/www/openstack-course-manager/')
activate_this = '/var/www/openstack-course-manager/.venv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))
from api import app as application
