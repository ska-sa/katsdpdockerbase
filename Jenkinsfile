#!groovy

@Library('katsdpjenkins') _

catchError {
    def images = ["docker-base", "docker-base-gpu",
                  "docker-base-runtime", "docker-base-build",
                  "docker-base-gpu-build", "docker-base-gpu-runtime"]
    for (image in images) {
        stage(image + ' image') {
            katsdp.simpleNode(timeout: [time: 1, unit: 'HOURS']) {
                deleteDir()
                checkout scm
                sh 'ln -s . katsdpdockerbase'   // So that build-docker-image.sh can be found
                katsdp.makeDocker(image, image)
            }
        }
    }
}

katsdp.mail('bmerry@ska.ac.za')
