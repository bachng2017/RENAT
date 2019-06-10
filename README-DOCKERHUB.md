## A glimpse of RENAT by docker
A super simple way to try RENAT is running it from a container. Below are instructions.

*Notes*: this container does not include proprietary softwares. See manuals for more details on how to install those.

1. import docker image from dockerhub

    ```
    $ docker pull bachng/renat:latest
    ```

2. start the container that open port 80 and 10022

    ```
    $ mkdir -p /opt/renat
    $ docker run --rm -d --privileged -v /opt/renat:/opt/renat -p 80:80 -p 10022:22 --name renat bachng/renat:latest
    ```

    At this point, a RENAT server will all necessary packages and latest RENAT is ready with predefined `robot` user.

    The folder `/opt/renat` on the container is also bound to `/opt/renat` on the host.

3. login to the container as `robot` user

    ```
    $ docker exec -it --user robot renat /bin/bash --login
    ```
    or using SSH with `robot/password!secret` account
    ```
    $ ssh -l robot -p 10022 <host_ip>
    ```

4. create a test scenario. Enter `y` to create a local configuration file and `Enter` for other questions.

    ```
    [robot@afeb42da1974 renat]$ $RENAT_PATH/tools/project.sh renat-sample
    [robot@afeb42da1974 renat]$ cd renat-sample
    [robot@afeb42da1974 renat]$ $RENAT_PATH/tools/item.sh test01
    ```

    A `do nothing` scenario is made. Check test01/main.robot for more details
5. run and check the result

    ```
    [robot@afeb42da1974 renat]$ cd test01
    [robot@afeb42da1974 renat]$ ./run.sh
    ```

    Test results and logs could be checked by `http://<this machine IP>/~robot/result.log`

6. to use with real devices for useful tests, edit below files for correct information
    - $RENAT_PATH/config/device.yaml: device's IP
    - $RENAT_PATH/config/auth.yaml: authentication (username/password)
    - $RENAT_PATH/config/template.yaml(optional): in case current templates are not fit for your devices

See [Create scenarios](#create-scenarios) for more detail about creating a sample to interact with routers.
