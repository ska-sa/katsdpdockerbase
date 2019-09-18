#!groovy

@Library('katsdpjenkins') _
katsdp.killOldJobs()

catchError {
    def images = ["docker-base-runtime", "docker-base-build",
                  "docker-base-gpu-build", "docker-base-gpu-runtime"]
    for (image in images) {
        // Don't publish images containing CUDA
        def push_external = (image.indexOf("gpu") == -1);
        stage(image + ' image') {
            katsdp.simpleNode(timeout: [time: 1, unit: 'HOURS']) {
                deleteDir()
                checkout scm
                sh 'ln -s . katsdpdockerbase'   // So that build-docker-image.sh can be found
                katsdp.makeDocker(image, image, null, push_external)
            }
        }
    }
}

katsdp.mail('sdpdev+katsdpdockerbase@ska.ac.za')
