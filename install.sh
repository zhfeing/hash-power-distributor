#!/bin/sh

port=13105
host=0.0.0.0

# usage
usage()
{
    echo "Hash power distributer installer.
    Usage:
    ./install.sh [-p | --python /absolute/path/to/python]"
}

install_path="/usr/local/hashpwd"
service_filepath="/etc/systemd/system/hashpwd.service"
exec_filepath="$install_path/src/main.py"
pid_filepath="/var/run/hashpwd.pid"
logger_path="/var/log/hashpwd/"


install()
{
    # check args
    if test "$1" = ""
    then
        echo "Error: lack of \"--python\" arg.\n"
        usage
        exit 1
    fi
    while test "$1" != ""
    do
        echo "001 $1\n"
        case $1 in
            -p | --python )
                shift
                python_exec=$1
                echo "Get python filepath: $python_exec \n"
                ;;
            -h | --help )
                usage
                exit
                ;;
            * )
                echo "Unknown option: $1\n"
                usage
                exit 1
        esac
        shift
    done

    echo "installing..."

    # make service file
    touch $service_filepath
    echo \
"[Unit]\n\
Description=Job that runs your user script\n\
\n\
[Service]\n\
ExecStart=$python_exec $exec_filepath --pid_filepath=$pid_filepath --host=$host --port=$port\n\
Type=oneshot\n\
RemainAfterExit=yes\n\
\n\
[Install]\n\
WantedBy=multi-user.target" > $service_filepath
    # copy files
    mkdir $install_path
    cp -r src $install_path/
    # configure daemon service
    systemctl daemon-reload
    systemctl enable hashpwd.service
    systemctl start hashpwd.service
}

uninstall()
{
    echo "Uninstalling..."
    systemctl stop hashpwd.service
    systemctl disable hashpwd.service
    systemctl daemon-reload
    rm $pid_filepath
    rm $service_filepath
    rm -r $install_path
    rm -r $logger_path
}

### Main

# check args
if test "$1" = ""
then
    echo "Error: Empty args\n"
    usage
    exit 1
fi

while test "$1" != ""
do
    case $1 in
        install )
            shift
            install $*
            shift; shift
            ;;
        
        uninstall )
            shift
            uninstall
            ;;
        -h | --help )
            usage
            exit
            ;;
        * )
            echo "Unknown option: $1\n"
            usage
            exit 1
    esac
done


