$( document ).ready(function() {
    check_cookie()
})

function check_cookie() {

  var page = location.href.split("/").slice(-1)[0]

  $.ajax({
    type: 'GET',
    withCredentials: true,
    url: '/api/token',
    statusCode: {
      401: function() {
        if(page != 'login.html') {
          logout()
        }
      },
      200: function() {
        if(page == 'login.html') {
          window.location.href = '/index.html'
        }
      }
    }
  }).done(function(data) {
    course = data.course
    $("#courseCode").html("Logged in as: " + course)
  })
}

function logout() {
  Cookies.remove('oscm', { path: '/' })
  window.location.href = '/login.html'
}
