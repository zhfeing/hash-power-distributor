#!/bin/sh

# usage
usage()
{
    echo "Hash power distributer installer.
    Usage:
    ./install.sh [-p | --python /absolute/path/to/python]"
}

service_filepath="/etc/systemd/system/hashpwd.service"
exec_filepath="/media/Data/project/hash-power-distributor/src/hash_power_distributer.py"
pid_filepath="/media/Data/project/hash-power-distributor/hashpwd.pid"


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
ExecStart=$python_exec $exec_filepath\n\
Type=oneshot\n\
RemainAfterExit=yes\n\
\n\
[Install]\n\
WantedBy=multi-user.target" > $service_filepath

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
    # rm $exec_filepath
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
    echo "0033 $1"
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


