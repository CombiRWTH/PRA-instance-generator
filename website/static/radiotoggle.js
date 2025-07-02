//This script serves to ensure radio buttons toggle correctly if they are not in the same form-group

async function run() {

    const radios = document.querySelectorAll('.radio-shared');

    // add event listener to all radio buttons
    for (var i = 0, length = radios.length; i < length; i++) {
        radios[i].addEventListener('change', function() {
            //deactivate all other radio buttons
            for (var i = 0, length = radios.length; i < length; i++) {
                if (radios[i].id != this.id) {
                    radios[i].checked = false;
                }
            }
        });
    }
}

window.onload = function() {
    run();
}
