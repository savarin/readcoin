
async function append(items) {
    const response = await fetch('./readcoin.wasm');
    const buffer = await response.arrayBuffer()
    const bytes = await WebAssembly.instantiate(buffer);
    const instance = bytes.instance;

    // Reduce list of numbers to total
    result = instance.exports.block_number_to_nonce(items)

    // Create new item for list
    const li = document.createElement('li');
    li.innerHTML = result.toString();

    // Add to task list
    document.querySelector('#tasks').append(li);
}


document.addEventListener('DOMContentLoaded', () => {

    // By default, submit button is disabled
    document.querySelector('#submit').disabled = true;

    // Enable button only if there is text in the input field
    document.querySelector('#task').onkeyup = () => {
        if (document.querySelector('#task').value.length > 0)
            document.querySelector('#submit').disabled = false;
        else
            document.querySelector('#submit').disabled = true;
    };

    document.querySelector('form').onsubmit = () => {

        // Parse numbers in input field and convert from strings to ints
        let items = document.querySelector('#task').value

        // Append sum of inputs as list item
        append(parseInt(items.trim(), 10));

        // Clear input field and disable button again
        document.querySelector('#task').value = '';
        document.querySelector('#submit').disabled = true;

        // Stop form from submitting
        return false;
    };
});
