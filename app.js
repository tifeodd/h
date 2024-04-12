var app = new Vue({
  el: '#app',
  data: {
    isLoggedIn: false,
    email: '',
    password: '',
    userEmail: '',
    originalUrl: '',
    urls: []
  },
  mounted() {
    const user = JSON.parse(localStorage.getItem('user'));
    if (user && user.email) {
      this.isLoggedIn = true;
      this.userEmail = user.email;
      this.fetchUrls();
    }
  },
  methods: {
    login() {
      if (this.email && this.password) {
        axios.post('https://cs3103.cs.unb.ca:8056/auth/login', {
          email: this.email,
          password: this.password
        })
        .then(response => {
          // Successful login
          this.isLoggedIn = true;
          this.userEmail = this.email;
          localStorage.setItem('user', JSON.stringify({ email: this.email }));
          this.fetchUrls();
          alert('Login successful!');
        })
        .catch(error => {
          console.error('Login failed:', error);
          alert('Login failed. Please try again.');
        });
      } else {
        alert('Please provide both email and password.');
      }
    },
    fetchUrls() {
      axios.get('https://cs3103.cs.unb.ca:8056/user/urls')
        .then(response => {
          // Check if response contains data and if 'urls' array is present
          if (response.data && response.data.length > 0 && response.data[0].urls) {
            this.urls = response.data[0].urls;
          } else {
            // Handle case where 'urls' array is not present in the response
            console.error('Invalid response format:', response.data);
            alert('Failed to fetch URLs. Response format is invalid.');
          }
        })
        .catch(error => {
          console.error('Failed to fetch URLs:', error);
          alert('Failed to fetch URLs. Please try again.');
        });
    },
   addUrl() {
        if (this.originalUrl) {
         axios.post('https://cs3103.cs.unb.ca:8056/urls', { url: this.originalUrl })
          .then(response => {
            // Check if response contains data
            if (response.data) {
              // Add the new URL to the urls array
              this.urls.push(response.data);
              // Clear the input field after successful addition
              this.originalUrl = '';
              this.fetchUrls();
            } else {
              console.error('Invalid response format:', response.data);
              alert('Failed to add URL. Response format is invalid.');
            }
          })
          .catch(error => {
            console.error('Failed to add URL:', error);
            alert('Failed to add URL. Please try again.');
          });
      } else {
        alert('Please provide a URL.');
      }
    },
    editUrl(index) {
        const oldUrl = this.urls[index].LongURL;
        const newUrl = prompt('Enter the new URL:');
        if (newUrl) {
            axios.put(`https://cs3103.cs.unb.ca:8056/urls`, { old_url: oldUrl, new_url: newUrl })
                .then(response => {
                    if (response.data) {
                        if (response.status === 409) {
                            alert('URL already exists in database under this user');
                        } else if (response.status === 200) {
                            this.urls[index].LongURL = newUrl;
                            alert('URL updated successfully');
                        }
                    } else {
                        console.error('Invalid response format:', response.data);
                        alert('Failed to update URL. Response format is invalid.');
                    }
                })
                .catch(error => {
                    console.error('Failed to update URL:', error);
                    alert('Failed to update URL. Please try again.');
                });
        } else {
            alert('Please provide a new URL.');
        }
    },
    deleteUrl(index) {
        const url = this.urls[index].LongURL;
        axios.delete(`https://cs3103.cs.unb.ca:8056/urls`, {
            data: { url: url },
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (response.status === 200) {
                this.urls.splice(index, 1);
                alert('URL deleted successfully');
            } else {
                console.error('Failed to delete URL:', response.data);
                alert('Failed to delete URL. Please try again.');
            }
        })
        .catch(error => {
            console.error('Failed to delete URL:', error);
            alert('Failed to delete URL. Please try again.');
        });
    },
    logout() {
      axios.delete('https://cs3103.cs.unb.ca:8056/auth/login')
        .then(() => {
          this.isLoggedIn = false;
          this.email = '';
          this.password = '';
          this.userEmail = '';
          localStorage.removeItem('user');
          this.urls = []; // Clear the urls array upon logout
          alert('Logout successful!');
        })
        .catch(error => {
          console.error('Logout failed:', error);
          alert('Logout failed. Please try again.');
        });
    }
  }
});





