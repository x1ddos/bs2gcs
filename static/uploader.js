(function Uploader(window){
	var doc = window.document,
	    imagesListElem;

	/**
	 * Hooks up uploader to elements on a page
	 * @param  {string} imagesListId
	 * @param  {string} inputId
	 * @param  {string} progressId
	 */
	function setup(imagesListId, inputId, progressId) {
		var input = doc.querySelector(inputId);
		if (!input)
			throw new Error('Could not find input elem ' + input);

		imagesListElem = doc.querySelector(imagesListId);
		input.addEventListener('change', function(event){
			var elem = this, createUploadURL = this.dataset.uploadUrl;
			if (!createUploadURL)
				throw new Error("Can't upload to nowhere");

			request('GET', createUploadURL, null, function(resp, xhr){
				uploadFiles(resp['url'], elem.files, doc.querySelector(progressId));
			});
		});
	}

	/**
	 * Uploads images to the backend.
	 * @param  {string} url
	 * @param  {Array.<File>} files
	 * @param  {Element} progressElem
	 */
	function uploadFiles(url, files, progressElem) {
		var payload = new FormData();
		for (var i=0, f; f=files[i]; ++i) {
	    payload.append(f.name, f);
	  }

	  var args = ['POST', url, payload, onUploadComplete];
	  if (progressElem)
	  	args.push(onUploadProgress.bind(progressElem))

		request.apply(null, args);
	}

	/**
	 * Callback during uploading. Shows upload progress.
	 * @param  {Event} event
	 */
	function onUploadProgress(event) {
		if (event.lengthComputable) {
      this.value = (event.loaded / event.total) * 100;
      this.textContent = this.value;  // fallback
    }
	}

	/**
	 * Callback when upload finishes.
	 * @param  {Array.<ImageItem>} data
	 */
	function onUploadComplete(data) {
		if (!data.length) return
		for (var i=0, item; item=data[i]; i++) {
			var media = doc.createElement('div');
			media.className = 'media';
			media.innerHTML = (
				'<div class="img"><img src="' + item.url + '=s100-c' + '"></div>' +
				'<div class="body">' +
					'URL: <a href="' + item.url + '">' + item.url + '</a><br>' +
					'GCS key: ' + item.gs_key + '<br>' +
					'Blob key: ' + item.blob_key +
					'<p>Updated: ' + item.updated + '</p>' +
				'</div>')
			imagesListElem.insertBefore(media, imagesListElem.firstChild);
		}
	}

	/**
	 * Create and execute AJAX request.
	 * @param  {string}   method
	 * @param  {string}   url
	 * @param  {*=}   data
	 * @param  {function(Object|Array, *)} callback
	 * @param  {function(Event)}   progressCallback
	 * @return {[type]}
	 */
	function request(method, url, data, callback, progressCallback) {
		var xhr = new XMLHttpRequest();
	  xhr.open(method, url, true);
	  if (progressCallback && xhr.upload)
	  	xhr.upload.onprogress = progressCallback;

	  xhr.onload = function() {
	  	if (xhr.status == 200) callback(JSON.parse(xhr.responseText), xhr)
	  }
	  xhr.send(data);
	  return xhr;
	}

	/**
	 * Public API
	 */
	window['Uploader'] = {
		setup: setup
	}
})(window);