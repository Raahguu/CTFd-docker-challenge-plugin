CTFd._internal.challenge.renderer = null;

CTFd._internal.challenge.preRender = function () {
  console.log("prerender");
};

CTFd._internal.challenge.render = null;

CTFd._internal.challenge.postRender = function () {
  console.log("postrender");
  checkContainerStatus();
};

function checkContainerStatus() {
  CTFd.fetch(`/docker/status/${CTFd._internal.challenge.data.id}`)
    .then((res) => {
      if (res.status == 403) {
        throw new Error("You cannot create a container unless logged in");
      }
      return res.json();
    })
    .then((data) => {
      if (data.success == false) {
        throw new Error(data.message);
      }
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
    })
    .catch((error) => {
      console.log(error);
      const error_box = document.getElementById("error_box");
      error_box.hidden = false;
      error_box.innerText = `${error.message || error}`;
    });
}

async function spawn_container() {
  // Spawn the container
  CTFd.fetch(`/docker/spawn/${CTFd._internal.challenge.data.id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
    .then((res) => {
      console.log(res);
      return res;
    })
    .then((res) => {
      if (res.status == 403) {
        throw new Error("You cannot create a container unless logged in");
      }
      return res.json();
    })
    .then((data) => {
      if (data.success === false) {
        if (data.error_code == 409) {
          throw new Error(
            `You already have a container running for ${data.challenge}`,
          );
        } else {
          throw new Error(`Unknown error code ${data.error_code}`);
        }
      }

      document.getElementById("no_container").hidden = true;
      document.getElementById("container_running").hidden = false;
      document.getElementById("ip").innerText = data.ip;
      document.getElementById("error_box").hidden = true;
      setExpiryTimer(data.expiry_time);
    })
    .catch((error) => {
      console.log(error);
      const error_box = document.getElementById("error_box");
      error_box.hidden = false;
      error_box.innerText = `Error: ${error.message || error}`;
    });
}

async function kill_container() {
  // Kill the existing container
  CTFd.fetch(`/docker/kill/${CTFd._internal.challenge.data.id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
    .then((res) => {
      console.log(res);
      return res;
    })
    .then((res) => {
      if (res.status == 403) {
        throw new Error("You cannot kill a container unless logged in");
      } else if (res.status == 404) {
        throw new Error(
          "You don't have a running container for this challenge",
        );
      }
      return res.json();
    })
    .then((data) => {
      if (data.success === false) {
        throw new Error(`Unknown error code ${data.error_code}`);
      }

      document.getElementById("no_container").hidden = false;
      document.getElementById("container_running").hidden = true;
      document.getElementById("error_box").hidden = true;
    })
    .catch((error) => {
      console.log(error);
      const error_box = document.getElementById("error_box");
      error_box.hidden = false;
      error_box.innerText = `Error: ${error.message || error}`;
    });
}

async function increase_expiry_time() {
  // Kill the existing container
  CTFd.fetch(`/docker/expiry/expand/${CTFd._internal.challenge.data.id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
    .then((res) => {
      console.log(res);
      return res;
    })
    .then((res) => {
      if (res.status == 403) {
        throw new Error("You cannot alter a container unless logged in");
      } else if (res.status == 404) {
        throw new Error(
          "You don't have a running container for this challenge",
        );
      }
      return res.json();
    })
    .then((data) => {
      if (data.success === false) {
        throw new Error(`Unknown error code ${data.error_code}`);
      }

      document.getElementById("error_box").hidden = true;
      setExpiryTimer(data.expiry_time);
    })
    .catch((error) => {
      console.log(error);
      const error_box = document.getElementById("error_box");
      error_box.hidden = false;
      error_box.innerText = `Error: ${error.message || error}`;
    });
}

CTFd._internal.challenge.submit = function (preview) {
  const challenge_id = parseInt(CTFd.lib.$("#challenge-id").val());
  var submission = CTFd.lib.$("#challenge-input").val();

  var body = {
    challenge_id: challenge_id,
    submission: submission,
  };
  var params = {};
  if (preview) {
    params["preview"] = true;
  }

  return CTFd.api.post_challenge_attempt(params, body).then((response) => {
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

function checkForCorrectFlag() {
  const challenge_window = document.getElementById("challenge");
  if (
    !challenge_window ||
    getComputedStyle(challenge_window).display === "none"
  ) {
    // Challenge window hidden or closed, stopping check
    clearInterval(checkInterval);
    checkInterval = null;
    return;
  }

  // Get the notification which says if the submission was correct or not
  const notification = document.querySelector(".notification-row .alert");
  // if it doesn't exist then the user has yet submit a flag
  if (!notification) return;

  // get the text box that containes the result message
  const strong = notification.querySelector("strong");
  if (!strong) return;

  // get the message containing the result
  const message = strong.textContent.trim();

  // if the message says that the flag submitted was correct
  if (
    message.toLocaleLowerCase().includes("correct") &&
    !message.toLocaleLowerCase().includes("incorrect")
  ) {
    clearInterval(checkInterval);
    checkInterval = null;
    kill_container();
  }
}

function setExpiryTimer(expiry_time) {
  const container_running = document.getElementById("container_running");
  const timer_minutes = document.getElementById("expiry_timer_minutes");
  const timer_seconds = document.getElementById("expiry_timer_seconds");

  if (container_running.hidden) {
    // the container was not started
    clearInterval(expiryTimerInterval);
    expiryTimerInterval = null;
    return;
  }

  let total_seconds_left = Math.floor(
    expiry_time - Math.floor(Date.now() / 1000),
  );

  let minutes_left = Math.floor(total_seconds_left / 60);
  let seconds_left = total_seconds_left % 60;

  timer_minutes.innerText = minutes_left;
  timer_seconds.innerText = seconds_left;

  if (expiryTimerInterval != null) {
    clearInterval(expiryTimerInterval);
  }
  expiryTimerInterval = setInterval(deincrementExpiryTimer, 1000);
}

function deincrementExpiryTimer() {
  const container_running = document.getElementById("container_running");
  const timer_minutes = document.getElementById("expiry_timer_minutes");
  const timer_seconds = document.getElementById("expiry_timer_seconds");

  if (container_running.hidden) {
    // the container was not started
    clearInterval(expiryTimerInterval);
    expiryTimerInterval = null;
    return;
  }

  // else the timer is still going
  let minutes_left = Number(timer_minutes.innerText);
  let seconds_left = Number(timer_seconds.innerText);
  if (!Number.isInteger(minutes_left) || !Number.isInteger(seconds_left)) {
    // the time_left does not display an integer
    timer_minutes.innerText = "?";
    timer_seconds.innerText = "?";
    clearInterval(expiryTimerInterval);
    expiryTimerInterval = null;
    return;
  }

  // the timer is valid and has not been messed with
  seconds_left--;

  // when time left expires
  if (seconds_left <= 0 && minutes_left <= 0) {
    const no_container = document.getElementById("no_container");

    checkContainerStatus();
    no_container.hidden = false;
    container_running.hidden = true;

    timer_minutes.innerText = 0;
    timer_seconds.innerText = 0;

    clearInterval(expiryTimerInterval);
    expiryTimerInterval = null;
    return;
  }

  if (seconds_left < 0) {
    minutes_left--;
    seconds_left = 59;
  }

  timer_minutes.innerText = minutes_left;
  timer_seconds.innerText = seconds_left;
}

if (!checkInterval) {
  var checkInterval = setInterval(checkForCorrectFlag, 1000);
}

if (!expiryTimerInterval) {
  var expiryTimerInterval = null;
}

function download_ovpn() {}
