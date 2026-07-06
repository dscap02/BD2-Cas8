function debounce(callback, delay = 300) {
    let timeoutId = null;

    return function (...args) {
        clearTimeout(timeoutId);

        timeoutId = setTimeout(
            () => callback.apply(this, args),
            delay
        );
    };
}

function showStatus(element, message, type = "info") {
    if (!element) {
        return;
    }

    element.className = `spotify-preview-status mt-3 alert alert-${type}`;
    element.textContent = message;
    element.classList.remove("d-none");
}

function setInputValue(id, value) {
    const element = document.getElementById(id);

    if (!element || value === undefined || value === null) {
        return;
    }

    element.value = value;
}

async function fetchSpotifyPreview() {
    const spotifyInput = document.getElementById("spotify_url");
    const statusBox = document.getElementById("spotify_preview_status");

    if (!spotifyInput || !statusBox) {
        return;
    }

    const spotifyUrl = spotifyInput.value.trim();

    if (spotifyUrl.length === 0) {
        showStatus(
            statusBox,
            "Incolla prima un link Spotify.",
            "warning"
        );

        return;
    }

    showStatus(
        statusBox,
        "Recupero dati da Spotify...",
        "info"
    );

    try {
        const response = await fetch(
            `/admin/api/spotify/preview?url=${encodeURIComponent(spotifyUrl)}`
        );

        const data = await response.json();

        if (!response.ok || !data.success) {
            showStatus(
                statusBox,
                data.message || "Impossibile recuperare i dati da Spotify.",
                "warning"
            );

            return;
        }

        const track = data.track;

        setInputValue("spotify_url", track.spotify_id);
        setInputValue("name", track.name);
        setInputValue("artist_name", track.artist_name);
        setInputValue("album_name", track.album_name);
        setInputValue("album_release_date", track.album_release_date);
        setInputValue("album_image_url", track.album_image_url);
        setInputValue("year", track.year);
        setInputValue("duration_minutes", track.duration_minutes);
        setInputValue("duration_seconds", track.duration_seconds);

        const sourceLabel = track.source === "spotify_web_api"
            ? "Spotify Web API"
            : "Spotify oEmbed";

        showStatus(
            statusBox,
            `Dati recuperati da ${sourceLabel}. Puoi modificarli prima di salvare.`,
            "success"
        );

    } catch (error) {
        showStatus(
            statusBox,
            "Errore durante il recupero dei dati Spotify.",
            "danger"
        );
    }
}

function clearSuggestions(container) {
    if (!container) {
        return;
    }

    container.innerHTML = "";
    container.classList.add("d-none");
}

function renderSuggestions(container, items, onSelect) {
    clearSuggestions(container);

    if (!items || items.length === 0) {
        return;
    }

    items.forEach((item) => {
        const button = document.createElement("button");

        button.type = "button";
        button.className = "autocomplete-item";

        button.textContent = item.label;

        button.addEventListener("click", () => {
            onSelect(item);
            clearSuggestions(container);
        });

        container.appendChild(button);
    });

    container.classList.remove("d-none");
}

async function searchTracks(query) {
    const response = await fetch(
        `/admin/api/tracks/search?q=${encodeURIComponent(query)}`
    );

    const tracks = await response.json();

    return tracks.map((track) => {
        const year = track.year ? ` (${track.year})` : "";

        return {
            id: track._id,
            label: `${track.name} — ${track.artist_name}${year}`,
        };
    });
}

async function searchListeners(query) {
    const response = await fetch(
        `/admin/api/listeners/search?q=${encodeURIComponent(query)}`
    );

    const listeners = await response.json();

    return listeners.map((listener) => {
        return {
            id: listener._id,
            label: listener.original_user_id,
        };
    });
}

function setupTrackAutocomplete() {
    const searchInput = document.getElementById("track_search");
    const hiddenInput = document.getElementById("track_id");
    const suggestionsBox = document.getElementById("track_suggestions");

    if (!searchInput || !hiddenInput || !suggestionsBox) {
        return;
    }

    searchInput.addEventListener("input", debounce(async () => {
        hiddenInput.value = "";

        const query = searchInput.value.trim();

        if (query.length < 2) {
            clearSuggestions(suggestionsBox);
            return;
        }

        const results = await searchTracks(query);

        renderSuggestions(
            suggestionsBox,
            results,
            (selectedTrack) => {
                searchInput.value = selectedTrack.label;
                hiddenInput.value = selectedTrack.id;
            }
        );
    }));
}

function setupListenerAutocomplete() {
    const searchInput = document.getElementById("listener_search");
    const hiddenInput = document.getElementById("listener_id");
    const suggestionsBox = document.getElementById("listener_suggestions");

    if (!searchInput || !hiddenInput || !suggestionsBox) {
        return;
    }

    searchInput.addEventListener("input", debounce(async () => {
        hiddenInput.value = "";

        const query = searchInput.value.trim();

        if (query.length < 2) {
            clearSuggestions(suggestionsBox);
            return;
        }

        const results = await searchListeners(query);

        renderSuggestions(
            suggestionsBox,
            results,
            (selectedListener) => {
                searchInput.value = selectedListener.label;
                hiddenInput.value = selectedListener.id;
            }
        );
    }));
}

function setupSpotifyPreview() {
    const spotifyButton = document.getElementById("spotify_preview_button");
    const spotifyInput = document.getElementById("spotify_url");

    if (!spotifyButton || !spotifyInput) {
        return;
    }

    spotifyButton.addEventListener(
        "click",
        fetchSpotifyPreview
    );

    spotifyInput.addEventListener(
        "change",
        fetchSpotifyPreview
    );
}

document.addEventListener("DOMContentLoaded", () => {
    setupSpotifyPreview();
    setupTrackAutocomplete();
    setupListenerAutocomplete();
});