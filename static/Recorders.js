// recorder.js — legacy file, recording is now handled inline in interview.html
// Kept for compatibility

let mediaRecorder;
let audioChunks = [];

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.start();
            audioChunks = [];
            mediaRecorder.ondataavailable = event => {
                audioChunks.push(event.data);
            };
        });
}

function stopRecording() {
    if (!mediaRecorder) return;
    mediaRecorder.stop();
    mediaRecorder.onstop = async () => {
        const blob = new Blob(audioChunks, { type: 'audio/wav' });
        const formData = new FormData();
        formData.append('audio_data', blob);

        const res = await fetch('/submit_voice', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.next) window.location.href = data.next;
    };
}