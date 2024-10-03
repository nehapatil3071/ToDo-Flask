function checkLogin(event) {
  if (!userLoggedIn) {
    event.preventDefault();  
    $('#loginModal').modal('show');  
  }
}