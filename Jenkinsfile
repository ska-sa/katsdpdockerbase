#!groovy

@Library('katsdpjenkins') _

catchError {
    stage('docker-base image') {
        katsdp.simpleNode(timeout: [time: 3, unit: 'HOURS']) {
            deleteDir()
            checkout scm
            katsdp.makeDocker('docker-base', 'docker-base')
        }
    }

    stage('docker-base-gpu image') {
        katsdp.simpleNode(timeout: [time: 3, unit: 'HOURS']) {
            deleteDir()
            checkout scm
            katsdp.makeDocker('docker-base-gpu', 'docker-base-gpu')
        }
    }
}

katsdp.mail('bmerry@ska.ac.za')
