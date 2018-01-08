#!groovy

@Library('katsdpjenkins') _

catchError {
    stage('docker-base image') {
        katsdp.simpleNode(timeout: [time: 3, unit: 'HOURS']) {
            deleteDir()
            checkout scm
            sh 'ln -s . katsdpdockerbase'   // So that build-docker-image.sh can be found
            katsdp.makeDocker('docker-base', 'docker-base')
        }
    }

    stage('docker-base-gpu image') {
        katsdp.simpleNode(timeout: [time: 3, unit: 'HOURS']) {
            deleteDir()
            checkout scm
            sh 'ln -s . katsdpdockerbase'   // So that build-docker-image.sh can be found
            katsdp.makeDocker('docker-base-gpu', 'docker-base-gpu')
        }
    }
}

katsdp.mail('bmerry@ska.ac.za')
