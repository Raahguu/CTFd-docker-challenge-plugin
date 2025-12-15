CTFd._internal.challenge.renderer = null;

CTFd._internal.challenge.preRender = function() {console.log('prerender')};

CTFd._internal.challenge.render = null;

CTFd._internal.challenge.postRender = function() {
    console.log('postrender')
    checkContainerStatus()
};

function checkContainerStatus() {
  CTFd.fetch(`/docker/status/${CTFd._internal.challenge.data.id}`)
  .then(res => res.json())
  .then(data => {
    if (data.status === false) {
      document.getElementById("no_container").hidden = false;
      document.getElementById("container_running").hidden = true;
      document.getElementById("error_box").hidden = true;
    } else {
      document.getElementById("no_container").hidden = true;
      document.getElementById("container_running").hidden = false;
      document.getElementById("ip").innerText = data.ip;
      document.getElementById("error_box").hidden = false;
    }
  });
}

async function spawn_container() {
  // Spawn the container
  CTFd.fetch(`/docker/spawn/${CTFd._internal.challenge.data.id}`, { 
      method: "POST", 
      headers: { 'Content-Type': 'application/json'},
    })
  .then(res => {
    console.log(res);
    return res;
  }).then(res => {
    if (res.status == 403) {
      throw new Error("You cannot create a container unless logged in")
    }
    return res.json()
  }).then(data => {
    if(data.success === false){
      if (data.error_code == 409) {
        throw new Error(`You already have a container running for ${data.challenge}`);
      } else {
        throw new Error(`Unknown error code ${data.error_code}`);
      }
    }

    document.getElementById("no_container").hidden = true;
    document.getElementById("container_running").hidden = false;
    document.getElementById("ip").innerText = data.ip;
    document.getElementById("error_box").hidden = true;
  }).catch(error => {
    console.log(error);
    error_box = document.getElementById("error_box");
    error_box.hidden = false;
    error_box.innerText = `Error: ${error.message || error}`;
  });
}

async function kill_container() {
  // Kill the existing container
  CTFd.fetch(`/docker/kill/${CTFd._internal.challenge.data.id}`, { 
      method: "POST", 
      headers: { 'Content-Type': 'application/json'},
    })
  .then(res => {
    console.log(res);
    return res;
  }).then(res => {
    if (res.status == 403) {
      throw new Error("You cannot kill a container unless logged in")
    } else if (res.status == 404) {
      throw new Error("You don't have a running container for this challenge");
    }
    return res.json()
  }).then(data => {
    if(data.success === false){
      throw new Error(`Unknown error code ${data.error_code}`);
    }

    document.getElementById("no_container").hidden = false;
    document.getElementById("container_running").hidden = true;
    document.getElementById("error_box").hidden = true;
  }).catch(error => {
    console.log(error);
    error_box = document.getElementById("error_box");
    error_box.hidden = false;
    error_box.innerText = `Error: ${error.message || error}`;
  });
}

CTFd._internal.challenge.submit = function(preview) {
  var challenge_id = parseInt(CTFd.lib.$("#challenge-id").val());
  var submission = CTFd.lib.$("#challenge-input").val();

  var body = {
    challenge_id: challenge_id,
    submission: submission
  };
  var params = {};
  if (preview) {
    params["preview"] = true;
  }

  return CTFd.api.post_challenge_attempt(params, body).then(response => {
    console.log("no");
    if (response.status === 429) {
      // User was ratelimited but process response
      return response;
    }
    if (response.status === 403) {
      // User is not logged in or CTF is paused.
      return response;
    }

    return response;
  });
};

function checkForCorrectFlag(){
  const challenge_window = document.getElementById("challenge")
  if (!challenge_window || getComputedStyle(challenge_window).display === 'none') {
    // Challenge window hidden or closed, stopping check
    clearInterval(checkInterval);
    checkInterval = null;
    return;
  }

  // Get the notification which says if the submission was correct or not
  const notification = document.querySelector('.notification-row .alert');
  // if it doesn't exist then the user has yet submit a flag
  if (!notification) return;

  // get the text box that containes the result message
  const strong = notification.querySelector('strong');
  if (!strong) return;

  // get the message containing the result
  const message = strong.textContent.trim();

  // if the message says that the flag submitted was correct
  if (message.toLocaleLowerCase().includes("correct") && !message.toLocaleLowerCase().includes("incorrect")) {
      clearInterval(checkInterval);
      checkInterval = null;
      kill_container()
  }
}

if (!checkInterval) {
    var checkInterval = setInterval(checkForCorrectFlag, 1000);
}