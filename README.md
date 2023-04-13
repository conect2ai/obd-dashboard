# OBD II Platform - Dashboard
This file contains instructions for running the OBD II Dashboard platform on Windows and Linux environments.

## Introduction
The OBD II Dashboard platform is a solution for monitoring vehicles and visualizing data. It was developed by Rodolfo Natan Silva Queiroz. The following technologies were used for the construction of the platform:

- PostgreSQL
- Flask
- Docker
- Node.js
- Vue.js
- Webpack

## Requirements
Before starting to run the application, you need to have the following requirements installed:

- Docker
- Git

To install Docker, you can follow the instructions available at: https://docs.docker.com/engine/install/.

To install Git, you can follow the instructions available at: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git.

## How to run the application
To run the OBD II Dashboard platform, follow the instructions below:

1. Open the terminal or command prompt in the directory where you want to save the project and execute the following command to clone the repository:
```
git clone https://github.com/rqroz/obd-dashboard.git
```
2. Navigate to the project directory using the command below:
```
cd obd-dashboard
```
3. In the root directory of the project, open the Dockerfile with a text editor and add the following lines before the last line `ENTRYPOINT ["scripts/run.sh"]`:
```
RUN chmod +x scripts/run.sh
RUN dos2unix scripts/run.sh
```
4. Save and close the Dockerfile.
5. Still in the Command Prompt or Terminal, execute the following command to create a Docker image of the platform:
```
docker image build -t image_name .
```
> NOTE: Replace "image_name" with a name of your choice for the Docker image.
6. Then, execute the following command to create a Docker container from the created image:
```
docker container run -it --publish 5000:5000 --name container_name image_name:latest
```
> NOTE: Replace "container_name" with a name of your choice for the Docker container. The `--publish` parameter maps the container's port 5000 to the host's port 5000, allowing you to access the platform in your browser.
7. Open a browser and go to the URL http://localhost:5000/index.html to view the OBD II Dashboard platform.

## Possible errors
### Execution of the `run.sh` script
If the application presents the error `exec scripts/run.sh: no such file or directory`, add the following lines in the Dockerfile, before the last line `ENTRYPOINT ["scripts/run.sh"]`:
```
RUN chmod +x scripts/run.sh 
RUN dos2unix scripts/run.sh
```

### Database error
If there is an error related to the database, replace "Binary" with "LargeBinary" in the file `app/models/user.py`.

### Flask error
If Flask-related errors occur, change `flask-sqlalchemy==2.4.1` to `flask-sqlalchemy==2.5.1` in the file `requirements/common.txt`.

For Linux, in addition to what was described, it is necessary to add the command `RUN pip install packaging` in the Dockerfile, right after the command `RUN pip install -r requirements/common.txt`.
