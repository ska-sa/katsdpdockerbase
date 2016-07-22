#!groovy

def katsdp = fileLoader.fromGit('scripts/katsdp.groovy', 'git@github.com:ska-sa/katsdpjenkins', 'master', 'katpull', '')

katsdp.commonBuild(maintainer: 'bmerry@ska.ac.za') {
    stage name: 'docker-base image', concurrency: 1
    katsdp.simpleNode(timeout: [time: 180, units: 'MINUTES']) {
        deleteDir()
        checkout scm
        stash 'source'
        katsdp.makeDocker('docker-base', 'docker-base')
    }

    stage name: 'docker-base-gpu image', concurrency: 1
    katsdp.simpleNode(timeout: [time: 180, units: 'MINUTES']) {
        deleteDir()
        unstash 'source'
        katsdp.makeDocker('docker-base-gpu', 'docker-base-gpu')
    }
}
