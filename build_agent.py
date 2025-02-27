import yaml
import subprocess
import os
import threading
import time
import concurrent.futures
import click
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

CONFIG_FILE = "/app/config.yaml"  # Mounted YAML config file

def load_yaml_config():
    """Load the YAML configuration file."""
    if not os.path.exists(CONFIG_FILE):
        print("❌ No configuration file found!")
        return None

    with open(CONFIG_FILE, "r") as file:
        return yaml.safe_load(file)


def execute_build_stages(jobs_or_stages, is_jobs=False):
    """
    Execute all stages or jobs of the build process in a single execution context.

    Args:
        jobs_or_stages (list): List of job or stage configurations.
        is_jobs (bool): True if processing multiple jobs; False if processing stages.

    Returns:
        None
    """
    summary = {"completed": 0, "failed": 0, "uploaded": 0}

    # Display unified build start header
    print("=" * 43)
    print("|" + " " * 41 + "|")
    print("|      DEVOPS-BOT INFRACYCLE BUILD STARTED       |")
    print("|" + " " * 41 + "|")
    print("=" * 43)
    print("")

    def simulate_build_progress():
        steps = [
            "🚀 Initializing DevOps-Bot...",
        ]
        for step in steps:
            print(f">> {step}")

    # Start the simulation in a separate thread
    simulation_thread = threading.Thread(target=simulate_build_progress)
    simulation_thread.start()

    # Helper function to process a single stage or job
    def process_single_item(item):
        stages = item.get("stages", []) if is_jobs else [item]
        for stage in stages:
            stage_name = stage.get("name", "Unnamed Stage")
            tasks = stage.get("tasks", {})
            ignore_failure = stage.get("ignore_failure", False)  # Default to False

            click.echo(f"[INFO] ***************** Started stage: {stage_name} *********************\n")

            try:
                # Setup and Clone
                if tasks.get("setup_and_clone", {}).get("enabled", False):
                    click.echo("📢 Setup and cloning are enabled in the configuration.")
                    click.echo("**************************** SETUP AND CLONING ENABLED *******************************")
                    clone_dir = setup_and_clone_repository(tasks.get("setup_and_clone", {}), summary)
                    if clone_dir:
                        click.echo("*********************** SETUP AND CLONING COMPLETED SUCCESSFULLY **************************")
                    else:
                        click.echo(click.style("*********************** SETUP AND CLONING FAILED **************************", fg="red"))
                        summary["failed"] += 1
                        if not ignore_failure:
                            click.echo(click.style(f"Stopping execution of stage '{stage_name}' due to failure.", fg="red"))
                            return
                    click.echo("")

                # Docker Build
                if tasks.get("docker_build", {}).get("enabled", False):
                    click.echo("🐳 Docker build is enabled in the configuration.")
                    click.echo("************************ DOCKER BUILD ENABLED *******************************")

                    result = docker_build(tasks.get("docker_build", {}), clone_dir, summary)
                    if result:
                        click.echo("✅ *********************** DOCKER BUILD COMPLETED SUCCESSFULLY **************************")
                    else:
                        click.echo(click.style("❌ *********************** DOCKER BUILD FAILED **************************", fg="red"))
                        summary["failed"] += 1
                        if not ignore_failure:
                            click.echo(click.style(f"Stopping execution of stage '{stage_name}' due to failure.", fg="red"))
                            return
                    click.echo("")

                # Docker Hub Push
                if tasks.get("docker_hub", {}).get("enabled", False):
                    click.echo("************************ DOCKER HUB PROCESS ENABLED *******************************")

                    result = push_to_docker_hub(
                        tasks.get("docker_hub", {}),
                        summary=summary
                    )

                    if result:
                        click.echo("✅ ************************ DOCKER HUB PROCESS COMPLETED *******************************")
                    else:
                        click.echo(click.style("❌ ************************ DOCKER HUB PROCESS FAILED *******************************", fg="red"))
                        summary["failed"] += 1
                        if not ignore_failure:
                            click.echo(click.style(f"Stopping execution of stage '{stage_name}' due to failure.", fg="red"))
                            return
                    click.echo("")

                # Shell Script Execution
                if tasks.get("sh", {}).get("enabled", False):
                    click.echo("************************ SHELL SCRIPT EXECUTION ENABLED *******************************")

                    result = run_shell_steps(tasks.get("sh", {}), summary)

                    if result:
                        click.echo("✅ *********************** SHELL SCRIPTS COMPLETED SUCCESSFULLY **************************")
                    else:
                        click.echo(click.style("❌ *********************** SHELL SCRIPTS FAILED **************************", fg="red"))
                        summary["failed"] += 1
                        if not ignore_failure:
                            click.echo(click.style(f"Stopping execution of stage '{stage_name}' due to failure.", fg="red"))
                            return
                    click.echo("")

                # Bash Script Execution
                if tasks.get("bash", {}).get("enabled", False):
                    click.echo("************************ BASH SCRIPT EXECUTION ENABLED *******************************")

                    result = run_bash_steps(tasks.get("bash", {}), summary)

                    if result:
                        click.echo("✅ *********************** BASH STEPS COMPLETED SUCCESSFULLY **************************")
                    else:
                        click.echo(click.style("❌ *********************** BASH STEPS FAILED **************************", fg="red"))
                        summary["failed"] += 1
                        if not ignore_failure:
                            click.echo(click.style(f"Stopping execution of stage '{stage_name}' due to failure.", fg="red"))
                            return
                    click.echo("")

                # Maven Build
                if tasks.get("maven", {}).get("enabled", False):
                    click.echo("📢 Maven build is enabled in the configuration.")
                    click.echo("************************ MAVEN BUILD ENABLED *******************************")

                    result = run_maven_build(tasks.get("maven", {}), clone_dir, summary)

                    if result:
                        click.echo("✅ *********************** MAVEN BUILD COMPLETED SUCCESSFULLY **************************")
                    else:
                        click.echo(click.style("❌ *********************** MAVEN BUILD FAILED **************************", fg="red"))
                        summary["failed"] += 1
                        if not ignore_failure:
                            click.echo(click.style(f"Stopping execution of stage '{stage_name}' due to failure.", fg="red"))
                            return
                    click.echo("")

                # Send Email Notification
                if tasks.get("send_notification", {}).get("enabled", False):
                    click.echo("************************ EMAIL NOTIFICATION ENABLED *******************************")

                    try:
                        result = notify_on_task_completion(
                            tasks.get("send_notification", {}).get("task_name", stage_name),
                            tasks.get("send_notification", {}).get("status", "success"),
                            tasks.get("send_notification", {}).get("recipients", []),
                            tasks.get("send_notification", {}).get("email_config", {})
                        )

                        if result:
                            click.echo("✅ ************************ EMAIL NOTIFICATION SENT *******************************")
                            summary["completed"] += 1  # Increment completed for successful notification
                        else:
                            click.echo(click.style("❌ ************************ EMAIL NOTIFICATION FAILED *******************************", fg="red"))
                            summary["failed"] += 1
                            if not ignore_failure:
                                click.echo(click.style(f"Stopping execution of stage '{stage_name}' due to failure.", fg="red"))
                                return
                    except Exception as e:
                        click.echo(click.style(f"❌ Error during notification: {str(e)}", fg="red"))
                        summary["failed"] += 1
                        if not ignore_failure:
                            return

                # Gradle Build
                if tasks.get("gradle", {}).get("enabled", False):
                    click.echo("📢 Gradle build is enabled in the configuration.")
                    click.echo("************************ GRADLE BUILD ENABLED *******************************")

                    result = run_gradle_build(tasks.get("gradle", {}), clone_dir, summary)

                    if result:
                        click.echo("✅ *********************** GRADLE BUILD COMPLETED SUCCESSFULLY **************************")
                    else:
                        click.echo(click.style("❌ *********************** GRADLE BUILD FAILED **************************", fg="red"))
                        summary["failed"] += 1
                        if not ignore_failure:
                            click.echo(click.style(f"Stopping execution of stage '{stage_name}' due to failure.", fg="red"))
                            return
                    click.echo("")

                # Trivy Scanning
                if tasks.get("trivy", {}).get("enabled", False):
                    click.echo("📢 Trivy scanning is enabled in the configuration.")
                    click.echo("************************ TRIVY SCANNING ENABLED *******************************")

                    result = run_trivy_scan(tasks.get("trivy", {}), summary)

                    if result:
                        click.echo("✅ *********************** TRIVY SCANNING COMPLETED SUCCESSFULLY **************************")
                    else:
                        click.echo(click.style("❌ *********************** TRIVY SCANNING FAILED **************************", fg="red"))
                        summary["failed"] += 1
                        if not ignore_failure:
                            click.echo(click.style(f"Stopping execution of stage '{stage_name}' due to failure.", fg="red"))
                            return
                    click.echo("")

                # Yarn Build
                if tasks.get("yarn", {}).get("enabled", False):
                    click.echo("📢 Yarn build is enabled in the configuration.")
                    click.echo("************************ YARN BUILD ENABLED *******************************")

                    result = run_yarn_build(tasks.get("yarn", {}), clone_dir, summary)

                    if result:
                        click.echo("✅ *********************** YARN BUILD COMPLETED SUCCESSFULLY **************************")
                    else:
                        click.echo(click.style("❌ *********************** YARN BUILD FAILED **************************", fg="red"))
                        summary["failed"] += 1
                        if not ignore_failure:
                            click.echo(click.style(f"Stopping execution of stage '{stage_name}' due to failure.", fg="red"))
                            return
                    click.echo("")

                # Go Build
                if tasks.get("go_build", {}).get("enabled", False):
                    click.echo("📢 Go Modules build is enabled in the configuration.")
                    click.echo("************************ GO BUILD ENABLED *******************************")

                    result = run_go_build(tasks.get("go_build", {}), clone_dir, summary)

                    if result:
                        click.echo("✅ *********************** GO BUILD COMPLETED SUCCESSFULLY **************************")
                    else:
                        click.echo(click.style("❌ *********************** GO BUILD FAILED **************************", fg="red"))
                        summary["failed"] += 1
                        if not ignore_failure:
                            click.echo(click.style(f"Stopping execution of stage '{stage_name}' due to failure.", fg="red"))
                            return
                    click.echo("")

                # NPM Build
                if tasks.get("npm", {}).get("enabled", False):
                    click.echo("📢 NPM build is enabled in the configuration.")
                    click.echo("************************ NPM BUILD ENABLED *******************************")

                    result = run_npm_build(tasks.get("npm", {}), clone_dir, summary)

                    if result:
                        click.echo("✅ *********************** NPM BUILD COMPLETED SUCCESSFULLY **************************")
                    else:
                        click.echo(click.style("❌ *********************** NPM BUILD FAILED **************************", fg="red"))
                        summary["failed"] += 1
                        if not ignore_failure:
                            click.echo(click.style(f"Stopping execution of stage '{stage_name}' due to failure.", fg="red"))
                            return
                    click.echo("")

                # SonarQube Analysis
                if tasks.get("sonarqube_analysis", {}).get("enabled", False):
                    click.echo("📢 SonarQube analysis is enabled in the configuration.")
                    click.echo("************************ SONARQUBE ANALYSIS ENABLED *******************************")

                    result = run_sonar_analysis(tasks.get("sonarqube_analysis", {}), clone_dir, summary)

                    if result:
                        click.echo("✅ *********************** SONARQUBE ANALYSIS COMPLETED SUCCESSFULLY **************************")
                    else:
                        click.echo(click.style("❌ *********************** SONARQUBE ANALYSIS FAILED **************************", fg="red"))
                        summary["failed"] += 1
                        if not ignore_failure:
                            click.echo(click.style(f"Stopping execution of stage '{stage_name}' due to failure.", fg="red"))
                            return
                    click.echo("")

                # Request Approval
                if tasks.get("request_approval", {}).get("enabled", False):
                    click.echo("************************ APPROVAL REQUEST ENABLED *******************************")

                    try:
                        approved = request_approval(tasks.get("request_approval", {}).get("task_name", stage_name))
                        if approved:
                            click.echo("✅ ************************ APPROVAL GRANTED *******************************")
                            summary["completed"] += 1
                        else:
                            click.echo(click.style("❌ ************************ APPROVAL DENIED *******************************", fg="red"))
                            summary["failed"] += 1
                            if not ignore_failure:
                                click.echo(click.style(f"Stopping execution of stage '{stage_name}' due to denied approval.", fg="red"))
                                return
                    except Exception as e:
                        click.echo(click.style(f"❌ Error during approval request: {str(e)}", fg="red"))
                        summary["failed"] += 1
                        if not ignore_failure:
                            return

            except Exception as e:
                click.echo(click.style(f"❌ Error during stage '{stage_name}': {str(e)}", fg="red"))
                summary["failed"] += 1

            click.echo(f"[INFO] ***************** Completed stage: {stage_name} *********************\n")

    # Execute jobs or stages
    if is_jobs:
        click.echo(f"Executing {len(jobs_or_stages)} jobs in parallel...\n")
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs_or_stages)) as executor:
            futures = [executor.submit(process_single_item, job) for job in jobs_or_stages]
            concurrent.futures.wait(futures)
    else:
        click.echo(f"Executing {len(jobs_or_stages)} stages sequentially...\n")
        for stage in jobs_or_stages:
            process_single_item(stage)

    simulation_thread.join()

    click.echo(f"Build process completed. Summary: {summary}")
    print("=" * 43)
    print("|      DEVOPS-BOT INFRACYCLE BUILD COMPLETED        |")
    print("=" * 43)

###################################
def run_yarn_build(yarn_config, clone_dir, summary):
    """
    Run Yarn build.

    Args:
        yarn_config (dict): Configuration dictionary for Yarn.
        clone_dir (str): The directory containing the source code.
        summary (dict): A dictionary to track the task results.

    Returns:
        bool: True if the Yarn build was successful, False otherwise.
    """
    if not yarn_config.get("enabled", True):
        click.echo(click.style("⚠️ Yarn build is not enabled; skipping this step.", fg="yellow"))
        return False

    click.echo("🚀 Starting Yarn build...")

    # Install dependencies
    yarn_install_command = f"cd {clone_dir} && yarn install"
    process = subprocess.Popen(yarn_install_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    for line in iter(process.stdout.readline, ''):
        click.echo(line, nl=False)

    process.stdout.close()
    process.wait()

    if process.returncode != 0:
        click.echo(click.style("❌ Failed to install Yarn dependencies.", fg="red"))
        summary["failed"] += 1
        return False

    # Execute Yarn build
    yarn_build_command = f"cd {clone_dir} && yarn build"
    process = subprocess.Popen(yarn_build_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    for line in iter(process.stdout.readline, ''):
        click.echo(line, nl=False)

    process.stdout.close()
    process.wait()

    if process.returncode != 0:
        click.echo(click.style("❌ Yarn build failed.", fg="red"))
        summary["failed"] += 1
        return False

    click.echo(click.style("✅ Yarn build completed successfully.", fg="green"))
    summary["completed"] += 1
    return True
def run_sonar_analysis(sonar_config, clone_dir, summary):
    """
    Run SonarQube analysis.

    Args:
        sonar_config (dict): Configuration dictionary for SonarQube.
        clone_dir (str): The directory containing the source code.
        summary (dict): A dictionary to track the task results.

    Returns:
        bool: True if the SonarQube analysis was successful, False otherwise.
    """
    if not sonar_config.get("enabled", True):
        click.echo(click.style("⚠️ SonarQube analysis is not enabled; skipping this step.", fg="yellow"))
        return False

    click.echo("🚀 Starting SonarQube analysis...")

    sonar_url = sonar_config.get("server_url")
    project_key = sonar_config.get("project_key")
    sonar_token = sonar_config.get("token")
    source_dir = sonar_config.get("source_dir", clone_dir)

    if not all([sonar_url, project_key, sonar_token]):
        click.echo(click.style("❌ SonarQube configuration is incomplete. Skipping analysis.", fg="red"))
        summary["failed"] += 1
        return False

    # Construct SonarQube command
    sonar_command = (
        f"sonar-scanner -Dsonar.projectKey={project_key} "
        f"-Dsonar.sources={source_dir} "
        f"-Dsonar.projectBaseDir={source_dir} "
        f"-Dsonar.host.url={sonar_url} "
        f"-Dsonar.login={sonar_token}"
    )

    # Execute SonarQube scan
    process = subprocess.Popen(sonar_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    for line in iter(process.stdout.readline, ''):
        click.echo(line, nl=False)

    process.stdout.close()
    process.wait()

    if process.returncode != 0:
        click.echo(click.style("❌ SonarQube analysis failed.", fg="red"))
        summary["failed"] += 1
        return False

    click.echo(click.style("✅ SonarQube analysis completed successfully.", fg="green"))
    summary["completed"] += 1
    return True
def run_npm_build(npm_config, clone_dir, summary):
    """
    Run npm build.

    Args:
        npm_config (dict): Configuration dictionary for npm.
        clone_dir (str): The directory containing the source code.
        summary (dict): A dictionary to track the task results.

    Returns:
        bool: True if the NPM build was successful, False otherwise.
    """
    if not npm_config.get("enabled", True):
        click.echo(click.style("⚠️ NPM build is not enabled; skipping this step.", fg="yellow"))
        return False

    click.echo("🚀 Starting NPM build...")

    # Install dependencies
    npm_install_command = f"cd {clone_dir} && npm install"
    process = subprocess.Popen(npm_install_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    for line in iter(process.stdout.readline, ''):
        click.echo(line, nl=False)

    process.stdout.close()
    process.wait()

    if process.returncode != 0:
        click.echo(click.style("❌ Failed to install npm dependencies.", fg="red"))
        summary["failed"] += 1
        return False

    # Execute npm build
    npm_build_command = f"cd {clone_dir} && npm run build"
    process = subprocess.Popen(npm_build_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    for line in iter(process.stdout.readline, ''):
        click.echo(line, nl=False)

    process.stdout.close()
    process.wait()

    if process.returncode != 0:
        click.echo(click.style("❌ NPM build failed.", fg="red"))
        summary["failed"] += 1
        return False

    click.echo(click.style("✅ NPM build completed successfully.", fg="green"))
    summary["completed"] += 1
    return True
def run_go_build(go_config, clone_dir, summary):
    """
    Run Go build process.

    Args:
        go_config (dict): Configuration dictionary for Go build.
        clone_dir (str): The directory containing the source code.
        summary (dict): A dictionary to track the task results.

    Returns:
        bool: True if the Go build was successful, False otherwise.
    """
    if not go_config.get("enabled", True):
        click.echo(click.style("⚠️ Go build is not enabled; skipping this step.", fg="yellow"))
        return False

    click.echo("🚀 Starting Go build...")

    # Initialize Go modules
    go_mod_init = f"cd {clone_dir} && go mod init"
    subprocess.run(go_mod_init, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Install dependencies
    go_get_command = f"cd {clone_dir} && go get ./..."
    subprocess.run(go_get_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Execute Go build
    go_build_command = f"cd {clone_dir} && go build -v"
    process = subprocess.Popen(go_build_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    for line in iter(process.stdout.readline, ''):
        click.echo(line, nl=False)

    process.stdout.close()
    process.wait()

    if process.returncode != 0:
        click.echo(click.style("❌ Go build failed.", fg="red"))
        summary["failed"] += 1
        return False

    click.echo(click.style("✅ Go build completed successfully.", fg="green"))
    summary["completed"] += 1
    return True

def run_trivy_scan(trivy_config, summary):
    """
    Run a Trivy scan.

    Args:
        trivy_config (dict): Configuration dictionary for Trivy.
        summary (dict): A dictionary to track the task results.

    Returns:
        bool: True if the scan was successful, False otherwise.
    """
    target_type = trivy_config.get("target_type", "image")  # "image" or "filesystem"
    target = trivy_config.get("target", "dob-trial-build:v6")
    output_format = trivy_config.get("format", "json")
    severity = trivy_config.get("severity", "UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL")

    # Construct Trivy scan command
    trivy_scan_command = f"trivy {target_type} {target} --format {output_format} --severity {severity}"

    click.echo(f"🔍 Running Trivy scan on {target}...")

    process = subprocess.Popen(
        trivy_scan_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    for line in iter(process.stdout.readline, ''):
        click.echo(line, nl=False)

    process.stdout.close()
    process.wait()

    if process.returncode != 0:
        click.echo(click.style("❌ Trivy scan failed.", fg="red"))
        summary["failed"] += 1
        return False

    click.echo(click.style("✅ Trivy scan completed successfully.", fg="green"))
    summary["completed"] += 1
    return True
def run_gradle_build(gradle_config, clone_dir, summary):
    """
    Run Gradle build.

    Args:
        gradle_config (dict): Configuration dictionary for Gradle.
        clone_dir (str): The directory containing the source code.
        summary (dict): A dictionary to track the task results.

    Returns:
        bool: True if the Gradle build was successful, False otherwise.
    """
    if not gradle_config.get("enabled", True):
        click.echo(click.style("⚠️ Gradle build is not enabled; skipping.", fg="yellow"))
        return False

    click.echo("🚀 Starting Gradle build...")

    gradle_tasks = gradle_config.get("target", "build")

    # Check if Gradle Wrapper exists
    check_gradlew_command = f"cd {clone_dir} && [ -f ./gradlew ] && echo 'found' || echo 'missing'"
    process = subprocess.run(check_gradlew_command, shell=True, capture_output=True, text=True)

    if "missing" in process.stdout:
        click.echo(click.style("⚠️ Gradle Wrapper (gradlew) not found. Using system Gradle.", fg="yellow"))
        gradle_command = f"cd {clone_dir} && gradle {gradle_tasks} --no-daemon"
    else:
        click.echo(click.style("✅ Using Gradle Wrapper (gradlew) for the build.", fg="green"))
        gradle_command = f"cd {clone_dir} && ./gradlew {gradle_tasks} --no-daemon"

    # Execute Gradle build
    process = subprocess.Popen(gradle_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    for line in iter(process.stdout.readline, ''):
        click.echo(line, nl=False)

    process.stdout.close()
    process.wait()

    if process.returncode != 0:
        click.echo(click.style("❌ Gradle build failed.", fg="red"))
        summary["failed"] += 1
        return False

    click.echo(click.style("✅ Gradle build completed successfully.", fg="green"))
    summary["completed"] += 1
    return True
def run_ant_build(ant_config, clone_dir, summary):
    """
    Run Ant build.

    Args:
        ant_config (dict): Configuration dictionary for Ant build.
        clone_dir (str): The directory containing the source code.
        summary (dict): A dictionary to track the task results.

    Returns:
        bool: True if the Ant build was successful, False otherwise.
    """
    if not ant_config.get("enabled", True):
        click.echo(click.style("⚠️ Ant build is not enabled; skipping.", fg="yellow"))
        return False

    click.echo("🚀 Starting Ant build...")

    # Ant-specific values
    build_file = ant_config.get("build_file", "build.xml")
    target = ant_config.get("target", "build")

    # Construct Ant build command
    ant_command = f"cd {clone_dir} && ant -f {build_file} {target}"

    click.echo(f"🔧 Executing Ant build command: {ant_command}")
    
    # Execute the Ant build
    process = subprocess.Popen(ant_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    for line in iter(process.stdout.readline, ''):
        click.echo(line, nl=False)

    process.stdout.close()
    process.wait()

    if process.returncode != 0:
        click.echo(click.style("❌ Ant build failed.", fg="red"))
        summary["failed"] += 1
        return False

    click.echo(click.style(f"✅ Ant build completed successfully.", fg="green"))
    summary["completed"] += 1
    return True

def run_maven_build(maven_config, clone_dir, summary):
    """
    Run Maven build inside the Build Agent container.

    Args:
        maven_config (dict): Configuration dictionary for Maven build.
        clone_dir (str): The directory containing the source code.
        summary (dict): A dictionary to track the task results.

    Returns:
        bool: True if the Maven build was successful, False otherwise.
    """
    if not maven_config.get("enabled"):
        click.echo(click.style("⚠️ Maven build is not enabled; skipping this step.", fg="yellow"))
        return False

    click.echo("🚀 Starting Maven build...")

    # Maven-specific configuration values
    project_pom = maven_config.get("project_pom", "pom.xml")
    maven_goals = maven_config.get("goals", "clean install")
    profiles = maven_config.get("profiles", "")
    profile_option = f"-P{profiles}" if profiles else ""
    output_dir = maven_config.get("output_dir", "/tmp/maven_artifacts")

    # Ensure the artifact directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Construct Maven build command
    maven_build_command = f"cd {clone_dir} && mvn -f {project_pom} {maven_goals} {profile_option} --batch-mode"

    # Execute Maven build command with real-time output
    click.echo(f"🔧 Executing: `{maven_build_command}`")
    process = subprocess.Popen(
        maven_build_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    for line in iter(process.stdout.readline, ''):
        click.echo(line, nl=False)  # Stream Maven output live

    process.stdout.close()
    process.wait()

    if process.returncode != 0:
        click.echo(click.style("❌ Maven build failed.", fg="red"))
        summary['failed'] += 1
        return False

    click.echo(click.style("✅ Maven build completed successfully.", fg="green"))

    # Move artifacts to the specified output directory
    move_artifacts_command = f"find {clone_dir}/target -type f -name '*.jar' -o -name '*.war' -exec mv {{}} {output_dir} \\;"
    subprocess.run(move_artifacts_command, shell=True, check=True)

    click.echo(click.style(f"📦 Artifacts moved to {output_dir}.", fg="green"))
    summary['completed'] += 1
    return True
def request_approval(task_name):
    # Prompt user for approval
    approval = click.prompt(f"Approval required for task '{task_name}'. Do you want to proceed? [y/N]", default='n')
    return approval.lower() == 'y'

def send_email_notification(task_name, status, recipients, email_config):
    """
    Send an email notification.

    Args:
        task_name (str): The name of the task.
        status (str): The task status (e.g., success, failure).
        recipients (list): List of recipient email addresses.
        email_config (dict): Email configuration containing SMTP details.

    Returns:
        bool: True if email was sent successfully, False otherwise.
    """
    smtp_server = email_config.get('smtp_server')
    smtp_port = email_config.get('smtp_port')
    sender_email = email_config.get('sender_email')
    sender_password = email_config.get('sender_password')

    if not (smtp_server and smtp_port and sender_email and sender_password):
        click.echo(click.style("❌ Incomplete email configuration. Please provide SMTP details.", fg="red"))
        return False

    subject = f"Task {task_name} - {status}"
    body = f"The task '{task_name}' has completed with status: {status}."

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, msg.as_string())
            click.echo(click.style(f"✅ Email notification sent to: {', '.join(recipients)}", fg="green"))
        return True
    except Exception as e:
        click.echo(click.style(f"❌ Failed to send email: {e}", fg="red"))
        return False
def notify_on_task_completion(task_name, status, recipients=None, email_config=None):
    """
    Notify users via email.

    Args:
        task_name (str): The task name.
        status (str): The task status (success, failure).
        recipients (list): List of email recipients.
        email_config (dict): SMTP email configuration.

    Returns:
        bool: True if notification was sent successfully, False otherwise.
    """
    if not recipients or not email_config:
        click.echo(click.style("❌ Email configuration or recipients are missing in config.", fg="red"))
        return False

    try:
        return send_email_notification(task_name, status, recipients, email_config)
    except Exception as e:
        click.echo(click.style(f"❌ Notification failed: {e}", fg="red"))
        return False
       
def run_shell_steps(sh_config, summary):
    """
    Execute custom shell commands inside the container.

    Args:
        sh_config (dict): Configuration dictionary for shell steps.
        summary (dict): A dictionary to track the task results.

    Returns:
        bool: True if all shell steps were executed successfully, False otherwise.
    """
    if not sh_config.get("enabled"):
        click.echo(click.style("⚠️ Shell script execution is not enabled; skipping this step.", fg="yellow"))
        return False

    click.echo("🚀 Starting custom Shell script execution...")
    steps = sh_config.get("steps", [])
    if not steps:
        click.echo(click.style("⚠️ No shell commands provided; skipping.", fg="yellow"))
        return False

    for i, command in enumerate(steps, start=1):
        click.echo(click.style(f"🔧 Executing Shell step {i}/{len(steps)}: {command}", fg="blue"))

        success, message = execute_command_locally(command, real_time_output=True)

        if success:
            click.echo(click.style(f"✅ Step {i} executed successfully.", fg="green"))
            summary['completed'] += 1
        else:
            click.echo(click.style(f"❌ Step {i} failed: {message}", fg="red"))
            summary['failed'] += 1
            return False

    return True
def run_bash_steps(bash_config, summary):
    """
    Execute custom Bash commands inside the container.

    Args:
        bash_config (dict): Configuration dictionary for Bash steps.
        summary (dict): A dictionary to track the task results.

    Returns:
        bool: True if all Bash steps were executed successfully, False otherwise.
    """
    if not bash_config.get("enabled"):
        click.echo(click.style("⚠️ Bash script execution is not enabled; skipping this step.", fg="yellow"))
        return False

    click.echo("🚀 Starting custom Bash script execution...")
    steps = bash_config.get("steps", [])
    if not steps:
        click.echo(click.style("⚠️ No Bash commands provided; skipping.", fg="yellow"))
        return False

    for i, command in enumerate(steps, start=1):
        click.echo(click.style(f"🔧 Executing Bash step {i}/{len(steps)}: {command}", fg="blue"))

        success, message = execute_command_locally(command, real_time_output=True)

        if success:
            click.echo(click.style(f"✅ Step {i} executed successfully.", fg="green"))
            summary['completed'] += 1
        else:
            click.echo(click.style(f"❌ Step {i} failed: {message}", fg="red"))
            summary['failed'] += 1
            return False

    return True

def execute_command_locally(command, real_time_output=False):
    """
    Execute a shell command locally inside the container.

    Args:
        command (str): The shell command to execute.
        real_time_output (bool): Whether to print real-time output of the command.

    Returns:
        tuple: (bool, str) where bool indicates success, and str contains output or error message.
    """
    try:
        if real_time_output:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in iter(process.stdout.readline, ''):
                click.echo(line, nl=False)
            process.stdout.close()
            process.wait()
            if process.returncode == 0:
                return True, "Command executed successfully."
            else:
                return False, f"Command failed with return code {process.returncode}."
        else:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, str(e)

def push_to_docker_hub(docker_hub, summary):
    """
    Push the Docker image to Docker Hub.

    Args:
        docker_hub (dict): Contains Docker Hub credentials, repository info, and built image name.
        summary (dict): A dictionary to track the task results.

    Returns:
        bool: True if the push to Docker Hub was successful, False otherwise.
    """
    docker_username = docker_hub.get("username")
    docker_password = docker_hub.get("password")
    repository_name = docker_hub.get("repository")
    built_image_name = docker_hub.get("built_image_name")
    image_tag = docker_hub.get("image_tag", "latest")
    full_image_name = f"{docker_username}/{repository_name}:{image_tag}"

    if not built_image_name:
        click.echo(click.style("❌ Built image name is missing in the configuration. Aborting Docker Hub push.", fg="red"))
        summary['failed'] += 1
        return False

    click.echo(f"📦 Preparing to push Docker image '{full_image_name}' to Docker Hub...")

    # Step 1: Ensure Docker is installed
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True, text=True)
        click.echo("✅ Docker is already installed.")
    except subprocess.CalledProcessError:
        click.echo(click.style("⚠️ Docker is not installed. Installing Docker...", fg="yellow"))
        subprocess.run("apt-get update && apt-get install -y docker.io", shell=True, check=True)

    # Step 2: Log in to Docker Hub
    click.echo("🔑 Logging in to Docker Hub...")
    try:
        login_command = f"echo {docker_password} | docker login -u {docker_username} --password-stdin"
        subprocess.run(login_command, shell=True, check=True)
    except subprocess.CalledProcessError:
        click.echo(click.style("❌ Failed to log in to Docker Hub.", fg="red"))
        summary['failed'] += 1
        return False

    # Step 3: Tag the Docker image
    click.echo(f"🏷️ Tagging Docker image '{built_image_name}' as '{full_image_name}'...")
    try:
        subprocess.run(f"docker tag {built_image_name} {full_image_name}", shell=True, check=True)
    except subprocess.CalledProcessError:
        click.echo(click.style("❌ Failed to tag Docker image.", fg="red"))
        summary['failed'] += 1
        return False

    # Step 4: Push the Docker image
    click.echo(f"🚀 Pushing Docker image '{full_image_name}' to Docker Hub...")
    try:
        subprocess.run(f"docker push {full_image_name}", shell=True, check=True)
        click.echo(click.style(f"✅ Docker image '{full_image_name}' pushed successfully.", fg="green"))
        summary['completed'] += 1
        return True
    except subprocess.CalledProcessError:
        click.echo(click.style("❌ Failed to push Docker image to Docker Hub.", fg="red"))
        summary['failed'] += 1
        return False
def check_docker_installation():
    """
    Check if Docker is installed inside the container.
    If not, install it using apt.

    Returns:
        bool: True if Docker is installed, False otherwise.
    """
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True, text=True)
        click.echo(click.style("✅ Docker is already installed.", fg="green"))
        return True
    except subprocess.CalledProcessError:
        click.echo(click.style("⚠️ Docker not found. Installing Docker...", fg="yellow"))
        install_docker()
        return False

def install_docker():
    """
    Install Docker inside the container using apt.
    """
    try:
        subprocess.run("apt-get update && apt-get install -y docker.io", shell=True, check=True)
        click.echo(click.style("✅ Docker installed successfully.", fg="green"))
    except subprocess.CalledProcessError as e:
        click.echo(click.style(f"❌ Failed to install Docker: {e}", fg="red"))

def docker_build(task, clone_dir, summary):
    """
    Perform a Docker build process inside the container.

    Args:
        task (dict): The task configuration containing Docker build details.
        clone_dir (str): The directory containing the Dockerfile and source code.
        summary (dict): A dictionary to track the task results.

    Returns:
        bool: True if the Docker build was successful, False otherwise.
    """
    if not task.get("enabled"):
        click.echo(click.style("⚠️ Docker build is not enabled; skipping this step.", fg="yellow"))
        return False

    click.echo("🐳 Starting Docker build...")

    # Ensure Docker is installed
    check_docker_installation()

    # Extract configuration
    dockerfile_path = task.get("dockerfile_path", f"{clone_dir}/Dockerfile")  # Default Dockerfile path
    build_tag = task.get("build_tag", "latest")
    image_name = task.get("image_name", "docker_image")
    built_image_name = f"{image_name}:{build_tag}"

    # Build Docker image
    docker_build_command = f"docker build -t {built_image_name} -f {dockerfile_path} {clone_dir}"
    click.echo(f"📦 Building Docker image '{built_image_name}' using Dockerfile at '{dockerfile_path}'...")

    try:
        subprocess.run(docker_build_command, shell=True, check=True)
        click.echo(click.style(f"✅ Docker image '{built_image_name}' built successfully.", fg="green"))
        summary['completed'] += 1
        return True
    except subprocess.CalledProcessError:
        click.echo(click.style(f"❌ Failed to build Docker image.", fg="red"))
        summary['failed'] += 1
        return False
def setup_and_clone_repository(tasks, summary):
    """
    Set up a directory and clone one or more branches of a repository inside the container.

    Args:
        tasks (dict): Task configuration containing 'clone_dir', 'source_url', 'branches', 'private_repo', 'username', and 'token'.
        summary (dict): A dictionary to track the task results.

    Returns:
        str: The path to the cloned directory if successful, or None on failure.
    """
    clone_dir = tasks.get("clone_dir", "/tmp/clone_repo_trial")
    source_url = tasks.get("source_url", "")
    branches = tasks.get("branches", ["main"])  # Default branch is 'main'
    private_repo = tasks.get("private_repo", False)
    username = tasks.get("username", "")
    token = tasks.get("token", "")

    if not source_url:
        click.echo(click.style("❌ No source URL provided for repository cloning.", fg="red"))
        summary['failed'] += 1
        return None

    # Step 1: Ensure Git is installed inside the container
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True, text=True)
        click.echo("✅ Git is already installed.")
    except subprocess.CalledProcessError:
        click.echo(click.style("❌ Git is not installed in the container. Installing Git...", fg="yellow"))
        subprocess.run("apt-get update && apt-get install -y git", shell=True, check=True)

    # Step 2: Prepare the directory
    click.echo(f"📁 Preparing {clone_dir} and cloning repository into it...")
    clear_and_create_command = f"rm -rf {clone_dir} && mkdir -p {clone_dir}"
    subprocess.run(clear_and_create_command, shell=True, check=True)

    # Step 3: Handle private repository authentication if necessary
    if private_repo:
        if not username or not token:
            click.echo(click.style("❌ Private repository credentials not provided.", fg="red"))
            summary['failed'] += 1
            return None
        # Construct the HTTPS URL with credentials
        protocol, repo_path = source_url.split("://", 1)
        source_url = f"{protocol}://{username}:{token}@{repo_path}"

    # Step 4: Clone the first branch directly into clone_dir
    first_branch = branches[0]
    clone_command = f"git clone --branch {first_branch} {source_url} {clone_dir}"
    try:
        subprocess.run(clone_command, shell=True, check=True)
        click.echo(click.style(f"✅ Branch '{first_branch}' successfully cloned into {clone_dir}.", fg="green"))
        summary['completed'] += 1
    except subprocess.CalledProcessError:
        click.echo(click.style(f"❌ Failed to clone branch '{first_branch}'.", fg="red"))
        summary['failed'] += 1
        return None

    # Step 5: Checkout additional branches if specified
    if len(branches) > 1:
        subprocess.run(f"cd {clone_dir} && git fetch", shell=True, check=True)

        for branch in branches[1:]:
            checkout_command = f"cd {clone_dir} && git checkout {branch}"
            try:
                subprocess.run(checkout_command, shell=True, check=True)
                click.echo(click.style(f"✅ Branch '{branch}' checked out in {clone_dir}.", fg="green"))
                summary['completed'] += 1
            except subprocess.CalledProcessError:
                click.echo(click.style(f"❌ Failed to check out branch '{branch}'.", fg="red"))
                summary['failed'] += 1
                return None

    return clone_dir

#######################################
def main():
    """Main execution function for the Build Agent."""
    print("🚀 Build Agent Started!")

    config = load_yaml_config()
    if not config:
        print("❌ No valid config. Exiting.")
        return

    # Extract jobs and execute them
    jobs = config.get("jobs", None)
    if jobs:
        print("🚀 Executing jobs from config...")
        execute_build_stages(jobs, is_jobs=True)

    print("🏁 Build Agent Execution Complete!")

if __name__ == "__main__":
    main()



