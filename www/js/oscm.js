$( document ).ready(function() {
    check_cookie()
})

function check_cookie() {

  var page = location.href.split("/").slice(-1)[0]

  $.ajax({
    type: 'GET',
    url: '/api/public/token',
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
  })
  .done(function(data) {
    course = data.course
    $("#courseCode").html(course)
  })
}

function logout() {

  $.ajax({
    type: 'GET',
    url: '/api/logout',
  })
  .always(function(data) {
    Cookies.remove('oscm', { path: '/' })
    window.location.href = '/login.html'
  })

}
