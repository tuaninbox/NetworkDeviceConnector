  let selectedDeviceId = "";
  let selectedDeviceName = "";
  let commandHistory = [];
  let historyIndex = -1;
  let deviceOutputs = {};     
  let activeDeviceTab = null; 

  document.getElementById("command-input").addEventListener("keydown", function(e) {
    if (e.key === "ArrowUp") {
      if (historyIndex > 0) {
        historyIndex--;
        this.value = commandHistory[historyIndex];
      }
      e.preventDefault();
    }

    if (e.key === "ArrowDown") {
      if (historyIndex < commandHistory.length - 1) {
        historyIndex++;
        this.value = commandHistory[historyIndex];
      } else {
        this.value = "";
      }
      e.preventDefault();
    }
  });

  //Enter key trigger runCommand() when not in interactive mode
  document.getElementById("command-input").addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();   // stops form submission or unwanted behaviour
      runCommand();         // runs your existing function
    }
  });

  // // ---------------------------
  // // Enter key sends command in interactive mode
  // // ---------------------------
  // document.getElementById("command-input").addEventListener("keydown", function(e) {
  //   if (e.key === "Enter") {
  //     if (ws) {
  //       ws.send(this.value + "\n");
  //       this.value = "";
  //     }
  //   }
  // });

  document.addEventListener("DOMContentLoaded", () => {
      const list = document.getElementById("device-list-ul");
      if (!list) return;

      list.addEventListener("click", (event) => {
        const li = event.target.closest("li");
        if (!li || !list.contains(li)) return;

        const deviceId = li.dataset.id;
        const deviceName = li.dataset.name;
        if (!deviceId) return;

        setSelectedDevice(deviceId, deviceName);

        list.querySelectorAll("li").forEach(item => item.classList.remove("bg-blue-100"));
        li.classList.add("bg-blue-100");
      });
  });

  window.addEventListener("scroll", () => {
    const selector = document.querySelector(".md\\:w-1\\/3"); // device selector container
    const dropdown = document.getElementById("device-dropdown");
    const arrow = document.getElementById("device-dropdown-arrow");

    const rect = selector.getBoundingClientRect();

    // If selector is no longer fully visible → collapse
    if (rect.bottom < 0 && !dropdown.classList.contains("hidden")) {
      dropdown.classList.add("hidden");
      arrow.textContent = "▼";
    }
  });


  // window.addEventListener("resize", () => {
  //   if (fitAddon) {
  //     fitAddon.fit();
  //     sendResize();
  //   }
  // });

  // ---------------------------
  // Run Command (HTTP)
  // ---------------------------
  async function runCommand() {
    const deviceId = getSelectedDevice();
    const deviceName = selectedDeviceName;
    const cmd = document.getElementById("command-input").value;

    // No device selected
    if (!deviceId) {
      // showInlinePopup("Select a device first");
      showMessage("Select a device first");
      return;
    }

    // No command entered
    if (!cmd) {
      showMessage("Input a command");
      return;
    }

    // Create tab ONLY if it does not exist
    if (!document.getElementById(`tab-${deviceId}`)) {
      deviceOutputs[deviceId] = "";
      addDeviceTab(deviceId, deviceName);
    }

    // Switch to this device's tab
    switchToDeviceTab(deviceId);

    const resp = await fetch(`/connector/${deviceId}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: cmd })
    });

    const data = await resp.json();
    if (!data.ok) {
      showMessage(data.error || "Command failed");
      return;
    }

    // alert(data.output || data.error || JSON.stringify(data));
    // Append output
    deviceOutputs[deviceId] += `\n${deviceName}# ${cmd}\n${data.output}\n`;

    // Update UI
    const outBox = document.getElementById("run-output");
    outBox.textContent = deviceOutputs[deviceId];
    outBox.scrollTop = outBox.scrollHeight;
  }

  // Sync Device
  async function syncDevices() {
    try {
      // Call backend refresh endpoint
      const resp = await fetch("/api/devices/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      if (!resp.ok) {
        const err = await resp.json();
        showMessage(err.detail || "Failed to sync devices from Nagios");
        return;
      }
      else {
        const stat = await resp.json();
        showMessage(stat.count || "No devices synced")
      }

      // Reload device list from backend
      const listResp = await fetch("/api/devices");
      if (!listResp.ok) {
        showMessage("Failed to reload device list");
        return;
      }
      else {
        const devices = await listResp.json();
        // Update UI table
        updateScrollableDeviceList(devices);
        showMessage("Device list updated");  
      }  
    } catch (e) {
      showMessage("Unexpected error syncing devices");
    }
  }

  // function appendOutput(text) {
  //   if (!term) return;
  //   term.write(text.replace(/\n/g, "\r\n"));
  // }

  function setSelectedDevice(deviceId, deviceName) {
    selectedDeviceId = deviceId;
    selectedDeviceName = deviceName;
    document.getElementById("selected-device").value = deviceId;
    document.getElementById("selected-device-name").value = deviceName;

    const title = document.getElementById("device-selector-title");
    title.textContent = `Run command on ${deviceName}`;

    const arrow = document.getElementById("device-dropdown-arrow");
    arrow.textContent = "▲";

    // // Create tab if not exists
    // if (!deviceOutputs[deviceId]) {
    //   deviceOutputs[deviceId] = "";
    //   addDeviceTab(deviceId, deviceName);
    // }

    // switchToDeviceTab(deviceId);
  }

  function getSelectedDevice() {
    return selectedDeviceId;
  }

  // ---------------------------
  // Show Command Error
  // ---------------------------
  function showMessage(msg) {
    const box = document.getElementById("command-error");
    box.textContent = msg;
    box.classList.remove("hidden");

    // Auto-hide after 3 seconds
    setTimeout(() => {
      box.classList.add("hidden");
    }, 3000);
  }


  function updateScrollableDeviceList(devices) {
    const ul = document.getElementById("device-list-ul");

    let html = "";
    for (const d of devices) {
      html += `
        <li class="px-3 py-2 cursor-pointer hover:bg-gray-100"
            data-id="${d.id}"
            data-name="${d.name}"
            onclick="selectDevice(this, '${d.id}', '${d.name}')">
          ${d.name} — ${d.ip} — ${d.os} — ${d.location}
        </li>
      `;
    }

    ul.innerHTML = html;
  }


  function addDeviceTab(deviceId, deviceName) {
    const tabs = document.getElementById("output-tabs");
    tabs.classList.remove("hidden");

    const tab = document.createElement("div");
    tab.id = `tab-${deviceId}`;
    tab.className = "flex items-center px-3 py-1 rounded bg-gray-200 hover:bg-gray-300 mr-1";

    // Tab label
    const label = document.createElement("button");
    label.textContent = deviceName;
    label.className = "tab-label mr-2";
    label.onclick = () => switchToDeviceTab(deviceId);

    // Close button
    const closeBtn = document.createElement("button");
    closeBtn.textContent = "×";
    closeBtn.className = "text-red-600 font-bold hover:text-red-800";
    closeBtn.onclick = (e) => {
      e.stopPropagation(); // prevent switching tab when clicking close
      closeDeviceTab(deviceId);
    };

    tab.appendChild(label);
    tab.appendChild(closeBtn);
    tabs.appendChild(tab);
  }

  function closeDeviceTab(deviceId) {
    const tab = document.getElementById(`tab-${deviceId}`);
    const deviceName = tab.querySelector(".tab-label").textContent;

    showConfirm(`Close tab for ${deviceName}?`, () => {

      // Remove tab element
      tab.remove();

      // Remove stored output
      delete deviceOutputs[deviceId];

      // If this tab was active, switch to another tab
      if (activeDeviceTab === deviceId) {
        const remainingTabs = document.querySelectorAll("#output-tabs > div");

        if (remainingTabs.length > 0) {
          const firstTab = remainingTabs[0];
          const newId = firstTab.id.replace("tab-", "");
          switchToDeviceTab(newId);
        } else {
          // No tabs left → clear UI
          activeDeviceTab = null;
          selectedDeviceId = "";
          selectedDeviceName = "";
          document.getElementById("selected-device").value = "";
          document.getElementById("selected-device-name").value = "";

          document.getElementById("run-output").textContent = "";
          document.getElementById("output-tabs").classList.add("hidden");

          const title = document.getElementById("device-selector-title");
          title.textContent = "Select a device to run command on";
        }
      }
    });
  }

  function switchToDeviceTab(deviceId) {
    activeDeviceTab = deviceId;
    selectedDeviceId = deviceId;
    
    const tab = document.getElementById(`tab-${deviceId}`);
    const deviceName = tab.querySelector(".tab-label").textContent;
    selectedDeviceName = deviceName;

    // Sync hidden fields
    document.getElementById("selected-device").value = deviceId;
    document.getElementById("selected-device-name").value = deviceName;

    // Update dropdown title
    const title = document.getElementById("device-selector-title");
    title.textContent = `Run command on ${deviceName}`;

    const arrow = document.getElementById("device-dropdown-arrow");
    arrow.textContent = "▼";

    // Highlight active tab
    document.querySelectorAll("#output-tabs div").forEach(btn => {
      btn.classList.remove("bg-blue-500", "text-white");
      btn.classList.add("bg-gray-200");
    });

    tab.classList.remove("bg-gray-200");
    tab.classList.add("bg-blue-500", "text-white");

    // Highlight device in list
    document.querySelectorAll("#device-list-ul li").forEach(li => {
      li.classList.remove("bg-blue-100");
      if (li.dataset.id === deviceId) {
        li.classList.add("bg-blue-100");
      }
    });

    // Show output box
    document.getElementById("run-output-container").classList.remove("hidden");
    // document.getElementById("terminal-container").classList.add("hidden");

    // Load output
    document.getElementById("run-output").textContent = deviceOutputs[deviceId];
  }


  function toggleDeviceDropdown() {
    const dd = document.getElementById("device-dropdown");
    const arrow = document.getElementById("device-dropdown-arrow");
    const title = document.getElementById("device-selector-title");

    const selectedName = document.getElementById("selected-device-name").value;

    dd.classList.toggle("hidden");

    if (dd.classList.contains("hidden")) {
      // Collapsed
      arrow.textContent = "▼";

      if (selectedName && selectedName.trim() !== "") {
        // Device selected → KEEP the title
        return;
      }

      // No device selected → show default
      title.textContent = "Select a device to run command on";

    } else {
      // Expanded
      arrow.textContent = "▲";

      if (!selectedName || selectedName.trim() === "") {
        title.textContent = "Select a device to run command on";
      }
    }
  }

  function filterDeviceList() {
    const keyword = document.getElementById("device-search").value.toLowerCase();
    const items = document.querySelectorAll("#device-list-ul li");

    items.forEach(li => {
      const text = li.textContent.toLowerCase();
      li.style.display = text.includes(keyword) ? "" : "none";
    });
  }

  function selectDevice(element, deviceId, deviceName) {
    setSelectedDevice(deviceId, deviceName);

    const items = document.querySelectorAll("#device-list-ul li");
    items.forEach(li => li.classList.remove("bg-blue-100"));
    element.classList.add("bg-blue-100");
  }

  function clearRunOutput() {
    if (!activeDeviceTab) return;

    // Clear stored output for this device
    deviceOutputs[activeDeviceTab] = "";

    // Clear UI output
    document.getElementById("run-output").textContent = "";

  }

  function copyRunOutput() {
    const text = document.getElementById("run-output").textContent;
    navigator.clipboard.writeText(text);
  }

  function saveRunOutput() {
    const text = document.getElementById("run-output").textContent;
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `${selectedDeviceName}_output.txt`;
    a.click();

    URL.revokeObjectURL(url);
  }

  function showConfirm(message, onConfirm) {
    const modal = document.getElementById("confirm-modal");
    const msg = document.getElementById("confirm-modal-message");
    const okBtn = document.getElementById("confirm-ok");
    const cancelBtn = document.getElementById("confirm-cancel");

    msg.textContent = message;

    modal.classList.remove("hidden");

    const cleanup = () => {
      modal.classList.add("hidden");
      okBtn.onclick = null;
      cancelBtn.onclick = null;
    };

    okBtn.onclick = () => {
      cleanup();
      onConfirm();
    };

    cancelBtn.onclick = cleanup;
  }

  function showInlinePopup(message) {
    const modal = document.getElementById("confirm-modal");
    const msg = document.getElementById("confirm-modal-message");
    const okBtn = document.getElementById("confirm-ok");
    const cancelBtn = document.getElementById("confirm-cancel");

    // Set message
    msg.textContent = message;

    // Change modal title
    document.getElementById("confirm-modal-title").textContent = "Notice";

    // Show modal
    modal.classList.remove("hidden");

    // Hide cancel button
    cancelBtn.style.display = "none";

    // Change OK button text
    okBtn.textContent = "OK";

    const cleanup = () => {
      modal.classList.add("hidden");
      okBtn.onclick = null;
      cancelBtn.onclick = null;
      cancelBtn.style.display = ""; // restore for next confirm modal
      okBtn.textContent = "Yes, close"; // restore default text
      document.getElementById("confirm-modal-title").textContent = "Confirm";

    };

    okBtn.onclick = cleanup;
  }
