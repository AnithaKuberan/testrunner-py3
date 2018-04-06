#!/bin/sh

function showHelp() {
    echo ""
    echo " Arguments:"
    echo "  --namespace [string]      Kubernetes namespace to use"
    echo "  --nodes [n]               Number of nodes to run"
    echo "  --cbversion [string]      Couchbase server version to use"
    echo "  --dockerhub [string]      Dockerhub account to use. Default is 'couchbase'"
    echo "  --targetCluster [string]  Select cluster type kubernetes / openshift"
    echo "  --cbOperatorVersion [string]  Couchbase operator version to use"
    echo ""
    exit 1
}

function validateArgs() {
    errCondition=false
    if [[ -z "$KUBENAMESPACE" ]]
    then
        echo "Exiting: KUBENAMESPACE not defined"
        errCondition=true
    fi

    if [ "$targetCluster" == "kubernetes" ]; then
        export KUBECONFIG=/root/.kube/kubernetes-config
    elif [ "$targetCluster" == "openshift" ]; then
        export KUBECONFIG=/root/.kube/openshift-config
        oc login -u system -p admin -n default
    else
        echo "Exiting: Invalid target cluster specified"
        errCondition=true
    fi

    if $errCondition
    then
        showHelp
    fi
}

function exitOnError() {
    if [ $1 -ne 0 ]
    then
        echo "Exiting: $2"
        cleanupFiles
        exit $1
    fi
}

function cleanupFiles() {
    rm -rf ${numOfNodes}node DockerFile testrunner.yaml
}

function cleanupCluster() {
    kubectl --namespace=$KUBENAMESPACE delete -f $testRunnerYamlFileName
    kubectl --namespace=$KUBENAMESPACE delete -f $cbClusterFile
    kubectl --namespace=$KUBENAMESPACE delete -f $deploymentFile
}

function downloadClusterYamlFiles() {
    wget https://packages.couchbase.com/kubernetes/beta/couchbase-cluster.yaml
    wget https://packages.couchbase.com/kubernetes/beta/secret.yaml
    wget https://packages.couchbase.com/kubernetes/beta/operator.yaml
}

function checkForClusterYamlFileExists() {
    for fileName in $deploymentFile $secretFile $cbClusterFile
    do
        if [ ! -f "$fileName" ]
        then
            exitOnError 1 "File '$fileName' not found!"
        fi
    done
}

function editClusterYamlFiles() {
    sed -i '/version:/{a\
        \ \ paused: false
        }' couchbase-cluster.yaml
    exitOnError $? "Unable to append version string in cbcluster yaml"

    sed -i "/name: couchbase-operator/{a\
        \ \ namespace: $KUBENAMESPACE
        }" operator.yaml
    exitOnError $? "Unable to append namespace string in cbcluster yaml"
}

function clearK8SCluster() {
    echo "Using name space '$KUBENAMESPACE'"
    kubectl --namespace=$KUBENAMESPACE delete deployment --all
    kubectl --namespace=$KUBENAMESPACE delete replicaset --all
    kubectl --namespace=$KUBENAMESPACE delete service -l app=couchbase
    kubectl --namespace=$KUBENAMESPACE delete jobs/testrunner
    kubectl --namespace=$KUBENAMESPACE delete pods -l name=couchbase-operator
    kubectl --namespace=$KUBENAMESPACE delete pods -l name=testrunner
    kubectl --namespace=$KUBENAMESPACE delete pods -l app=couchbase
    kubectl --namespace=$KUBENAMESPACE delete --all couchbaseclusters
    kubectl --namespace=$KUBENAMESPACE delete secrets basic-test-secret

    echo "Waiting for all pods to be cleaned up.."
    while [ true ]
    do
        if [ $(kubectl --namespace=$KUBENAMESPACE get pods | grep "NAME" | wc -l | awk '{print $1}') -eq 0 ]
        then
            break
        fi
        sleep 5
    done
}

function waitForPodToStartRunning() {
    echo "Initializing pod '$1'"
    for i in {1..300}
    do
        podRunning=$(kubectl --namespace=$KUBENAMESPACE describe pod $1 | grep "State:" | grep "Running" | wc -l | xargs )
        if [ $podRunning -eq 1 ]; then
            break
        fi
        sleep 1
    done

    if [ $podRunning -ne 1 ]; then
        exitOnError 1 "Pod '$1' not started running even after 5mins"
    fi
    unset podRunning
}

function checkForCbClusterPodsReady () {
    reqPodNum=$1
    clusterPrefix=$2
    podsReady=false

    echo "Waiting for all cb cluster pods to be up and running.."
    for i in {1..60}
    do
        currPodNum=$(kubectl --namespace=$KUBENAMESPACE get pods -l app=couchbase | grep Running | wc -l)
        if [ $currPodNum -eq $reqPodNum ]
        then
            podsReady=true
            break
        fi
        sleep 5
    done

    if [ "$podsReady" == "false" ]
    then
        exitOnError 1 "Pods not ready even after 5 mins wait time"
    fi
}

function pushDockerImage() {
    dockerImageName=$1
    tarFileName=$2

    baseName=$(echo $dockerImageName | cut -d":" -f 1)
    tagName=$(echo $dockerImageName | cut -d":" -f 2)
    dockerImageId=$(docker image ls | grep "$baseName" | grep "$tagName" | awk '{print $3}')
    echo "Created docker image '$baseName:$tagName' with id '$dockerImageId'"

    docker tag $dockerImageId $baseName:$tagName
    docker push $dockerImageName
    exitOnError $? "Unable to push docker image '$baseName:$tagName' '$dockerImageId' to dockerhub"

    if [ "$tarFileName" != "" ]
    then
        docker save -o ./$tarFileName $dockerImageName
        exitOnError $? "Unable to save docker image '$baseName:$tagName' '$dockerImageId' to '$tarFileName' locally"
    fi

    unset baseName tagName dockerImageId
}

function createTestrunnerDockerfile() {
    dockerFileString=""
    #dockerFileString="${dockerFileString}FROM ubuntu:15.04\n"
    #dockerFileString="${dockerFileString}RUN apt-get update\n"
    #dockerFileString="${dockerFileString}RUN apt-get install -y gcc g++ make cmake git-core libevent-dev libev-dev libssl-dev libffi-dev psmisc iptables zip unzip python-dev python-pip vim curl\n"
    #dockerFileString="${dockerFileString}# build libcouchbase\n"
    #dockerFileString="${dockerFileString}RUN git clone git://github.com/couchbase/libcouchbase.git && mkdir libcouchbase/build\n"
    #dockerFileString="${dockerFileString}\n"
    #dockerFileString="${dockerFileString}WORKDIR libcouchbase/build\n"
    #dockerFileString="${dockerFileString}RUN ../cmake/configure --prefix=/usr && make && make install\n"
    #dockerFileString="${dockerFileString}\n"
    #dockerFileString="${dockerFileString}WORKDIR /\n"
    #dockerFileString="${dockerFileString}RUN git clone git://github.com/couchbase/testrunner.git\n"
    #dockerFileString="${dockerFileString}WORKDIR testrunner\n"
    #dockerFileString="${dockerFileString}ARG BRANCH=master\n"
    #dockerFileString="${dockerFileString}RUN git checkout \$BRANCH\n"
    #dockerFileString="${dockerFileString}\n"
    #dockerFileString="${dockerFileString}# install python deps\n"
    #dockerFileString="${dockerFileString}RUN pip2 install --upgrade packaging appdirs\n"
    #dockerFileString="${dockerFileString}RUN pip install -U pip setuptools\n"
    #dockerFileString="${dockerFileString}RUN pip install paramiko && pip install gevent && pip install boto && pip install httplib2 && pip install pyyaml && pip install couchbase\n"
    #dockerFileString="${dockerFileString}\n"
    #dockerFileString="${dockerFileString}COPY getNodeIps.py getNodeIps.py\n"

    dockerFileString="${dockerFileString}FROM ashwin2002/testrunner-cloud:baseimage\n"
    #dockerFileString="${dockerFileString}COPY entrypoint.sh entrypoint.sh\n"
    dockerFileString="${dockerFileString}COPY ${numOfNodes}node.ini ${numOfNodes}node.ini\n"
    dockerFileString="${dockerFileString}COPY testcases.conf testcases.conf\n"
    dockerFileString="${dockerFileString}RUN chmod +x ./entrypoint.sh\n"
    dockerFileString="${dockerFileString}ENTRYPOINT [\"./entrypoint.sh\", \"$numOfNodes\"]\n"

    printf "$dockerFileString" > $testrunnerDir/Dockerfile
}

function createTestCaseFile() {
    testCaseFileString=""
    testCaseFileString="${testCaseFileString}recreatebuckettests.RecreateMembaseBuckets.test_default_moxi\n"
    testCaseFileString="${testCaseFileString}deletebuckettests.DeleteMembaseBuckets.test_non_default_moxi\n"
    testCaseFileString="${testCaseFileString}createbuckettests.CreateMembaseBucketsTests.test_default_moxi\n"
    testCaseFileString="${testCaseFileString}createbuckettests.CreateMembaseBucketsTests.test_default_on_non_default_port\n"
    testCaseFileString="${testCaseFileString}createbuckettests.CreateMembaseBucketsTests.test_non_default_case_sensitive_different_port\n"
    testCaseFileString="${testCaseFileString}createbuckettests.CreateMembaseBucketsTests.test_two_replica\n"
    testCaseFileString="${testCaseFileString}createbuckettests.CreateMembaseBucketsTests.test_valid_length,name_length=100\n"
    testCaseFileString="${testCaseFileString}setgettests.MembaseBucket.test_value_100b\n"
    testCaseFileString="${testCaseFileString}expirytests.ExpiryTests.test_expired_keys\n"
    testCaseFileString="${testCaseFileString}memcapable.GetlTests.test_getl_expired_item\n"
    testCaseFileString="${testCaseFileString}memcapable.GetlTests.test_getl_thirty\n"

    testCaseFileString="${testCaseFileString}# memory sanity tests\n"
    testCaseFileString="${testCaseFileString}memorysanitytests.MemorySanity.check_memory_stats,sasl_buckets=1,standard_buckets=1,items=2000\n"
    testCaseFileString="${testCaseFileString}drainratetests.DrainRateTests.test_drain_100k_items\n"
    testCaseFileString="${testCaseFileString}view.viewquerytests.ViewQueryTests.test_employee_dataset_all_queries,limit=1000,docs-per-day=2,wait_persistence=true,timeout=1200,nodes_init=1\n"

    testCaseFileString="${testCaseFileString}CCCP.CCCP.test_get_config_client,standard_buckets=1,sasl_buckets=1\n"
    testCaseFileString="${testCaseFileString}CCCP.CCCP.test_not_my_vbucket_config\n"
    testCaseFileString="${testCaseFileString}flush.bucketflush.BucketFlushTests.bucketflush_with_data_ops_moxi,items=5000,data_op=create,use_ascii=False\n"

    testCaseFileString="${testCaseFileString}### Security - Audit + LDAP - LDAP will run separately in sanity tests ####\n"
    testCaseFileString="${testCaseFileString}security.audittest.auditTest.test_bucketEvents,default_bucket=false,id=8201,ops=create\n"

    testCaseFileString="${testCaseFileString}### N1ql ####\n"
    testCaseFileString="${testCaseFileString}tuqquery.tuq_index.QueriesViewsTests.test_primary_create_delete_index,doc-per-day=3,force_clean=True,reload_data=False,nodes_init=1\n"
    testCaseFileString="${testCaseFileString}tuqquery.tuq_index.QueriesViewsTests.test_primary_create_delete_index,doc-per-day=2,primary_indx_type=GSI,reload_data=False,force_clean=True,nodes_init=1\n"
    testCaseFileString="${testCaseFileString}tuqquery.tuq_index.QueriesViewsTests.test_explain_index_attr,force_clean=True,reload_data=False,doc-per-day=2,nodes_init=1\n"
    testCaseFileString="${testCaseFileString}tuqquery.tuq_dml.DMLQueryTests.test_sanity,force_clean=True,reload_data=False,nodes_init=1,skip_load=True,nodes_init=1\n"


    testCaseFileString="${testCaseFileString}### WATSON FEAUTURES ###\n"
    testCaseFileString="${testCaseFileString}#Covering Index and CBQ\n"
    testCaseFileString="${testCaseFileString}tuqquery.tuq_2i_index.QueriesIndexTests.test_covering_index,covering_index=true,doc-per-day=1,skip_index=True,index_type=gsi,force_clean=True,reload_data=True\n"
    testCaseFileString="${testCaseFileString}tuqquery.tuq_advancedcbqshell.AdvancedQueryTests.test_engine_postive\n"

    testCaseFileString="${testCaseFileString}#Subdoc\n"
    testCaseFileString="${testCaseFileString}subdoc.subdoc_nested_dataset.SubdocNestedDataset.test_sanity\n"
    testCaseFileString="${testCaseFileString}tuqquery.tuq_2i_index.QueriesIndexTests.test_simple_array_index,index_type=GSI,array_indexing=True,force_clean=True,reload_data=True\n"

    printf "$testCaseFileString" > ${numOfNodes}node/testcases.conf
    exitOnError $? "Unable to create testcases.conf file"
}

function createNodeIniFile() {
    nodeIniFileString=""
    nodeIniFileString="${nodeIniFileString}[global]\n"
    nodeIniFileString="${nodeIniFileString}port:8091\n"
    nodeIniFileString="${nodeIniFileString}username:root\n"
    nodeIniFileString="${nodeIniFileString}password:couchbase\n"
    nodeIniFileString="${nodeIniFileString}index_port:9102\n"
    nodeIniFileString="${nodeIniFileString}n1ql_port:18903\n"
    nodeIniFileString="${nodeIniFileString}\n"

    nodeIniFileString="${nodeIniFileString}[servers]\n"
    for index in $(seq 1 $numOfNodes)
    do
       nodeIniFileString="${nodeIniFileString}$index:vm$index\n"
    done
    nodeIniFileString="${nodeIniFileString}\n"

    for index in $(seq 1 $numOfNodes)
    do
        nodeIniFileString="${nodeIniFileString}[vm$index]\n"
        nodeIniFileString="${nodeIniFileString}ip:172.17.1.1\n"
        nodeIniFileString="${nodeIniFileString}services=n1ql,kv,index\n"
        nodeIniFileString="${nodeIniFileString}\n"
    done

    nodeIniFileString="${nodeIniFileString}[membase]\n"
    nodeIniFileString="${nodeIniFileString}rest_username:Administrator\n"
    nodeIniFileString="${nodeIniFileString}rest_password:password\n"

    printf "$nodeIniFileString" > ${numOfNodes}node/${numOfNodes}node.ini
    exitOnError $? "Unable to create node.ini file"
}

function copyFilesForTestRunnerImage() {
    mkdir -p ${numOfNodes}node

    createTestCaseFile
    createNodeIniFile
    createTestrunnerDockerfile

    # Create node config files #
    for fileName in $testrunnerDir/Dockerfile $testrunnerDir/entrypoint.sh $testrunnerDir/getNodeIps.py
    do
        if [ ! -f "$fileName" ]; then
            cd ..
            exitOnError 1 "File '$fileName' not found!"
        fi
        cp $fileName ${numOfNodes}node
    done
}

function exportDockerImageToNodes() {
    dockerImageName=$1
    imageName=$(echo $dockerImageName | cut -d':' -f 1)
    tagName=$(echo $dockerImageName | cut -d':' -f 2)

    tarFileName="dockerImage.tar"
    rm -f $tarFileName
    echo "Creating docker image tar file '$tarFileName'"
    docker save -o $tarFileName $dockerImageName

    for nodeIp in 172.23.99.12 172.23.99.13 172.23.99.27 172.23.99.29
    do
        echo "Deleting exiting docker image in the server '$nodeIp'"
        sshpass -p "couchbase" ssh -o StrictHostKeyChecking=no -t root@$nodeIp docker images | grep $imageName | grep $tagName | awk '{print $3}' | xargs docker rmi -f

        echo "Copying '$tarFileName' to '$nodeIp:/root/' path"
        sshpass -p "couchbase" scp $tarFileName root@$nodeIp:/root/

        echo "Loading Docker image.."
        sshpass -p "couchbase" ssh -o StrictHostKeyChecking=no -t root@$nodeIp docker load -i /root/$tarFileName
        sshpass -p "couchbase" ssh -o StrictHostKeyChecking=no -t root@$nodeIp rm -f /root/$tarFileName
    done
    
    echo "Deleting the tar file '$tarFileName'"
    rm -f $tarFileName
    unset dockerImageName tarFileName nodeIp imageName tagName
}

function buildCbServerDockerImage() {
    dockerFileString="FROM couchbase/server:enterprise-${serverVersion}\n"
    dockerFileString="${dockerFileString}MAINTAINER Couchbase Docker Team <docker@couchbase.com>\n"
    dockerFileString="${dockerFileString}RUN apt update\n"
    dockerFileString="${dockerFileString}RUN apt install openssh-client openssh-server -y\n"
    dockerFileString="${dockerFileString}RUN mkdir /var/run/sshd\n"
    dockerFileString="${dockerFileString}RUN echo 'root:couchbase' | chpasswd\n"
    dockerFileString="${dockerFileString}RUN sed -i 's/PermitRootLogin .*\$/PermitRootLogin yes/' /etc/ssh/sshd_config\n"
    dockerFileString="${dockerFileString}RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd\n"
    dockerFileString="${dockerFileString}RUN echo 'export VISIBLE=now' >> /etc/profile\n"
    dockerFileString="${dockerFileString}EXPOSE 8091 8092 8093 8094 9100 9101 9102 9103 9104 9105 9998 9999 11207 11210 11211 18091 18092 22\n"

    dockerFileString="${dockerFileString}RUN echo '#!/bin/bash' > myentrypoint.sh\n"
    dockerFileString="${dockerFileString}RUN echo 'service ssh start' >> myentrypoint.sh\n"
    dockerFileString="${dockerFileString}RUN echo '/entrypoint.sh couchbase-server' >> myentrypoint.sh\n"
    dockerFileString="${dockerFileString}RUN chmod +x myentrypoint.sh\n"
    dockerFileString="${dockerFileString}ENTRYPOINT [\"/myentrypoint.sh\"]\n"

    printf "$dockerFileString" > Dockerfile
    docker build . -t $cbServerDockerImageName
    exitOnError $? "Unable to create docker image"
    exportDockerImageToNodes $cbServerDockerImageName
    #pushDockerImage $cbServerDockerImageName
}

function buildTestRunnerImage() {
    copyFilesForTestRunnerImage

    # Build testrunner docker file #
    cd ${numOfNodes}node
    docker build . -t $testRunnerDockerImageName
    exitOnError $? "Failed to build testrunner docker image"
    exportDockerImageToNodes $testRunnerDockerImageName
    #pushDockerImage $testRunnerDockerImageName
    cd ..
}

function deployCluster() {
    imageName=$(echo $cbServerDockerImageName | cut -d':' -f 1)
    tagName=$(echo $cbServerDockerImageName | cut -d':' -f 2)

    echo "Using operator image '$cbOperatorImage'"
    sed -i -e "s#image: couchbase\/couchbase-operator:v1#image: $cbOperatorImage#" $deploymentFile

    sed -i "s/paused: true/paused: false/" $cbClusterFile
    exitOnError $? "Unable to replace pause string in cbcluster yaml"

    sed -i "s#baseImage:.*\$#baseImage: $imageName#" $cbClusterFile
    exitOnError $? "Unable to replace baseImage string in cbcluster yaml"

    sed -i "s/version:.*$/version: $tagName/" $cbClusterFile
    exitOnError $? "Unable to replace version string in cbcluster yaml"

    sed -i "s/size:.*$/size: $numOfNodes/" $cbClusterFile
    exitOnError $? "Unable to replace size in cbcluster yaml"

    echo "Cat '$cbClusterFile':"
    cat $cbClusterFile

    unset imageName tagName

    kubectl --namespace=$KUBENAMESPACE create -f $secretFile
    kubectl --namespace=$KUBENAMESPACE create -f $deploymentFile

    echo "Creating couchbase-operator pod"
    podReady=false
    for i in {1..60}
    do
        podName=$(kubectl --namespace=$KUBENAMESPACE get pods -l name=couchbase-operator | tail -1 | awk '{print $1}')
        if [ "$podName" != "" ]; then
            waitForPodToStartRunning $podName
            podReady=true
            break
        fi
        sleep 5
    done

    if ! $podReady
    then
        exitOnError 1 "Operator pod not started running even after 5mins"
    fi

    kubectl --namespace=$KUBENAMESPACE create -f $cbClusterFile
    checkForCbClusterPodsReady $numOfNodes "$clusterName"
}

function pauseCbOperator() {
    sed -i "s/paused: false/paused: true/g" $cbClusterFile
    exitOnError $? "Unable to replace string in cbcluster yaml"

    kubectl --namespace=$KUBENAMESPACE apply -f $cbClusterFile
    exitOnError $? "Unable to pause the cbcluster"
}

function createTestRunnerYamlFile() {
    fileString=""
    fileString="${fileString}apiVersion: batch/v1\n"
    fileString="${fileString}kind: Job\n"
    fileString="${fileString}metadata:\n"
    fileString="${fileString}  name: testrunner\n"
    fileString="${fileString}spec:\n"
    fileString="${fileString}  template:\n"
    fileString="${fileString}    metadata:\n"
    fileString="${fileString}      labels:\n"
    fileString="${fileString}        name: testrunner\n"
    fileString="${fileString}    spec:\n"
    fileString="${fileString}      containers:\n"
    fileString="${fileString}      - name: testrunner\n"
    fileString="${fileString}        image: $testRunnerDockerImageName\n"
    fileString="${fileString}      restartPolicy: Never\n"
    echo "---" > $testRunnerYamlFileName
    printf "$fileString" >> $testRunnerYamlFileName

    echo "$testRunnerYamlFileName file content:"
    cat $testRunnerYamlFileName
}

cd cloudtest

# Variable declaration and parsing argument#
KUBENAMESPACE="default"
numOfNodes=$numOfNodes
serverVersion=$cbversion
dockerHubAccount=$dockerhub
targetCluster=$targetCluster
cbOperatorVersion=1.0.0-162
testrunnerPodName=""

while [ $# -ne 0 ]
do
    case "$1" in
        "--namespace")
            KUBENAMESPACE=$2
            shift ; shift
            ;;
        "--nodes")
            numOfNodes=$2
            re='^[0-9]+$'
            if ! [[ $numOfNodes =~ $re ]] ; then
               echo "Exiting: Invalid '$1' value. Should be an integer"
               showHelp
            fi
            shift ; shift
            ;;
        "--cbversion")
            serverVersion=$2
            shift ; shift
            ;;
        "--dockerhub")
            dockerHubAccount=$2
            shift ; shift
            ;;
        "--targetCluster")
            targetCluster=$2
            shift ; shift
            ;;
        "--cbOperatorVersion")
            cbOperatorVersion=$2
            shift ; shift
            ;;
        *)
            echo "Exiting: Invalid argument '$1'"
            showHelp
    esac
done

validateArgs

if [ ! -z $cbOperatorVersion ]
then
    cbOperatorImage="couchbase/couchbase-operator-internal:$cbOperatorVersion"
else
    cbOperatorImage=$(sh /root/latest-docker-tag.sh)
fi

deploymentFile="operator.yaml"
secretFile="secret.yaml"
cbClusterFile="couchbase-cluster.yaml"
testrunnerDir="support"
testRunnerYamlFileName="testrunner.yaml"
clusterName=$(grep "name:" $cbClusterFile | head -1 | xargs | cut -d' ' -f 2)

cbServerDockerImageName="${dockerHubAccount}/couchbase-server:custom-${serverVersion}"
testRunnerDockerImageName="${dockerHubAccount}/testrunner-cloud:customImage"

declare -a podIpArray

# Build required images #
buildCbServerDockerImage
clearK8SCluster
deployCluster
pauseCbOperator

buildTestRunnerImage
createTestRunnerYamlFile
kubectl --namespace=$KUBENAMESPACE create -f $testRunnerYamlFileName
exitOnError $? "Unable to start testrunner container"

# Wait for testrunner pod to get created
while true
do
    testrunnerPodName=$(kubectl --namespace=$KUBENAMESPACE get -l job-name=testrunner pods | tail -1 | awk '{print $1}')
    if [ "$testrunnerPodName" != "" ]; then
        waitForPodToStartRunning $testrunnerPodName
        break
    fi
done

# Redirect logs from testrunner pod
echo "Logs from testrunner pod '$testrunnerPodName':"
kubectl --namespace=$KUBENAMESPACE logs --follow=true $testrunnerPodName &

# Wait for testrunner job to complete
while [ true ]
do
    currTestrunnerPod=$(kubectl --namespace=$KUBENAMESPACE get -l job-name=testrunner pods | tail -1 | awk '{print $1}')
    if [ "$currTestrunnerPod" != "$testrunnerPodName" ]; then
        echo "Testrunner pod '$testrunnerPodName' replaced with new pod '$currTestrunnerPod'"
        kill %1
        kubectl --namespace=$KUBENAMESPACE delete pod $testrunnerPodName

        testrunnerPodName=$currTestrunnerPod
        waitForPodToStartRunning $testrunnerPodName

        echo "Logs from new testrunner pod '$testrunnerPodName':"
        kubectl --namespace=$KUBENAMESPACE logs --follow=true $testrunnerPodName &
    fi

    isJobCompleted=$(kubectl --namespace=$KUBENAMESPACE logs $testrunnerPodName --tail=10 | grep "Testrunner: command completed" | wc -l)
    if [ $isJobCompleted -eq 1 ]; then
        kill %1
        break
    fi
    sleep 10
done

cleanupCluster
cleanupFiles

exit 0

