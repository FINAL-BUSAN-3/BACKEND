pipeline {

	agent any
	stages {
		stage('test-stage') {
			steps {
				slackSend(channel: '#deployment-alert', color: '#0000FF' , message: "[TEST]STARTED: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL})")
			}
		}
		
	}
}
