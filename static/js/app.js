document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('youtube-url-input');
    const searchButton = document.getElementById('search-button');
    const songList = document.getElementById('song-list');
    const videoContainer = document.getElementById('video-container');
    const rightColumn = document.querySelector('.right-column');
    const playlistTitleContainer = document.getElementById('playlist-title-container');
    const playlistTitleInput = document.getElementById('playlist-title-input');
    const savePlaylistContainer = document.querySelector('.save-setlist-container');
    const saveSetlistButton = document.getElementById('save-setlist-button');
    const loadingIndicator = document.getElementById('loading-indicator');
    const loginButton = document.getElementById('login-button');
    const currentService = document.querySelector('.current-service');
    const switchService = document.querySelector('.switch-service');
    const navLinks = document.querySelectorAll('nav a');
    const rightColumnContent = document.getElementById('right-column-content');
    const contentSections = document.querySelectorAll('.content-section');
    let activeService = 'spotify';
    let isLoggedIn = false;

    document.getElementById('feedback-form').addEventListener('submit', function(e) {
        e.preventDefault();
    
        const feedbackText = document.getElementById('feedback-text').value.trim();
    
        // Check if the feedback text is empty
        if (!feedbackText) {
            alert('Please enter your feedback before submitting.');
            return; // Exit the function early, so no request is made
        }
    
        fetch('/submit_feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ feedback: feedbackText }),
        })
        .then(response => response.json())
        .then(data => {
            // Clear the previous alerts
            if (data.message) {
                alert('Thank you for your feedback!');
                document.getElementById('feedback-text').value = '';  // Clear the text area
            } else if (data.error) {
                alert('Failed to send feedback: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while sending your feedback. Please try again.');
        });
    });
    
    

    function updateServiceDisplay() {
        const spotifyLogo = '<img src="/static/images/spotify-logo.png" alt="Spotify" class="service-logo">';
        const appleLogo = '';
        
        if (activeService === 'spotify') {
            document.getElementById('login-button').textContent = 'Login with Spotify';
            document.querySelector('.current-service').innerHTML = `You are saving playlists with ${spotifyLogo} Spotify`;
            document.querySelector('.switch-service').innerHTML = `Switch to ${appleLogo} MUSIC`;
            document.querySelector('.service-selection span').innerHTML = `Saving with ${spotifyLogo} Spotify.`;
            document.querySelector('.service-toggle span').innerHTML = `Switch to ${appleLogo} MUSIC`;
        } else {
            document.getElementById('login-button').textContent = 'Login with  MUSIC';
            document.querySelector('.current-service').innerHTML = `You are saving playlists with ${appleLogo} Apple Music`;
            document.querySelector('.switch-service').innerHTML = `Switch to ${spotifyLogo} Spotify`;
            document.querySelector('.service-selection span').innerHTML = `Saving with ${appleLogo} Apple Music.`;
            document.querySelector('.service-toggle span').innerHTML = `Switch to ${spotifyLogo} Spotify`;
        }
    }

    document.querySelector('.service-toggle').addEventListener('click', toggleService);

    function updateSaveButton() {
        if (isLoggedIn) {
            saveSetlistButton.textContent = 'Save Playlist';
            saveSetlistButton.disabled = false;
        } else {
            saveSetlistButton.textContent = 'LOGIN TO SAVE';
            saveSetlistButton.disabled = true;
        }
    }

    loginButton.addEventListener('click', function(e) {
        if (activeService === 'apple') {
            alert("Saving to Apple Music is not available yet. We're working on it!");
            return;
        }
        e.preventDefault();
        window.location.href = `/login/${activeService}`;
    });

    // Check if user is logged in
    fetch('/current_user')
        .then(response => response.json())
        .then(data => {
            if (data.logged_in) {
                isLoggedIn = true;
                loginButton.textContent = `${data.display_name}`;
                updateSaveButton();
            } else {
                isLoggedIn = false;
                loginButton.textContent = 'Login with Spotify';
                updateSaveButton();
            }
        })
        .catch(error => console.error('Error:', error));

    function toggleService() {
        activeService = activeService === 'spotify' ? 'apple' : 'spotify';
        updateServiceDisplay();
        updateColors();
    }

    function updateColors() {
        const topBar = document.querySelector('.top-bar');
        const saveSetlistButton = document.querySelector('.save-setlist-button');
        if (activeService === 'spotify') {
            topBar.style.backgroundColor = '#38CB82';
            saveSetlistButton.style.backgroundColor = '#38CB82';
            document.body.setAttribute('data-service', 'spotify');
        } else {
            topBar.style.backgroundColor = '#FF7F7F';
            saveSetlistButton.style.backgroundColor = '#FF7F7F';
            document.body.setAttribute('data-service', 'apple');
        }
    }

    function showLoading() {
        document.getElementById('loading-indicator').style.display = 'flex';
    }

    function hideLoading() {
        document.getElementById('loading-indicator').style.display = 'none';
    }

    switchService.addEventListener('click', toggleService);

    searchButton.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });

    function handleSearch() {
        showLoading();
        const youtubeUrl = searchInput.value.trim();
        if (youtubeUrl) {
            playlistTitleContainer.style.display = 'block';
            loadingIndicator.style.display = 'block';
            songList.innerHTML = '';
            videoContainer.innerHTML = '';
            savePlaylistContainer.style.display = 'none';
    
            fetch('/get_video_title', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ youtube_url: youtubeUrl })
            })
            .then(response => response.json())
            .then(data => {
                playlistTitleInput.value = `Setlist: ${data.title}`;
            })
            .catch(error => {
                console.error('Error fetching video title:', error);
                playlistTitleInput.value = `Setlist: ${new Date().toLocaleDateString()}`;
            });
    
            fetch('/embed', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: youtubeUrl })
            })
            .then(response => response.json())
            .then(data => {
                if (data.html) {
                    videoContainer.innerHTML = data.html;
                    analyzeVideo(youtubeUrl);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                loadingIndicator.textContent = 'Failed to embed video.';
            })
            .finally(() => {
            });
        }
    }

    function analyzeVideo(url) {
        fetch('/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ youtube_url: url })
        })
        .then(response => response.json())
        .then(data => {
            displayResults(data);
        })
        .catch(error => {
            console.error('Error:', error);
            loadingIndicator.textContent = 'Failed to analyze video.';
        });
    }

    function displayResults(songs) {
        loadingIndicator.style.display = 'none';
        playlistTitleContainer.style.display = 'block';

        songs.forEach(song => {
            const li = document.createElement('li');
            li.innerHTML = `
                <img src="${song.albumArt}" alt="${song.title} album art">
                <div class="song-info">
                    <span class="song-title">${song.title}</span>
                    <span class="song-artist">${song.artist}</span>
                </div>
            `;
            li.addEventListener('click', function() {
                let url;
                if (activeService === 'spotify') {
                    url = song.spotifyLink;
                } else {
                    url = song.appleMusicLink;
                }
                window.open(url, '_blank'); // Open the link in a new tab
            });
            songList.appendChild(li);
        });

        savePlaylistContainer.style.display = 'block';
        hideLoading()
    }

    saveSetlistButton.addEventListener('click', savePlaylist);

    function savePlaylist() {
        if (!isLoggedIn) {
            alert('Please log in to save the playlist.');
            return;
        }
        if (activeService === 'apple') {
            alert('Apple Music Support is WIP!');
            return;
        }

        const playlistTitle = playlistTitleInput.value;
        const tracks = Array.from(songList.children).map(li => ({
            title: li.querySelector('.song-title').textContent,
            artist: li.querySelector('.song-artist').textContent
        }));

        fetch('/save_playlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: playlistTitle,
                tracks: tracks,
                service: activeService
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Playlist saved successfully!');
            } else {
                alert('Failed to save playlist: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while saving the playlist.');
        });
    }

    document.querySelector('.facebook-share').addEventListener('click', () => {
        window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(window.location.href)}`, '_blank');
    });

    document.querySelector('.twitter-share').addEventListener('click', () => {
        window.open(`https://twitter.com/intent/tweet?url=${encodeURIComponent(window.location.href)}`, '_blank');
    });

    document.querySelector('.copy-link').addEventListener('click', () => {
        navigator.clipboard.writeText(window.location.href).then(() => {
        });
    });

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = e.target.getAttribute('href').substring(1);
            updateContent(targetId);
        });
    });

    serviceToggle.addEventListener('click', () => {
        currentService = currentService === 'spotify' ? 'apple' : 'spotify';
        updateColors();
        updateServiceDisplay();
    });

    function updateContent(targetId) {
        contentSections.forEach(section => section.classList.remove('active'));
        document.getElementById(targetId).classList.add('active');
        
        navLinks.forEach(link => link.classList.remove('active'));
        document.querySelector(`nav a[href="#${targetId}"]`).classList.add('active');
    }

    // Initialize
    updateServiceDisplay();
    updateColors();
    updateSaveButton();
});
