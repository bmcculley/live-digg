$(document).ready(function(){
  console.log("Jquery ready!");
  showHideMenu();

  var favicon=new Favico({
    animation:'popFade'
  });
  
  var newcount = 1;
  
  if ("WebSocket" in window) {
    var ws = new WebSocket("ws://" + location.host + "/realtime/");
    ws.onopen = function() {};
    console.log("WebSocket connection made.");
    ws.onmessage = function (event) {
      var entry = jQuery.parseJSON(event.data);
      // increase the favicon count
      favicon.badge(newcount);
      
      $('#entries').prepend('<div class="entry"><h2 class="e-title"><a href="' + entry.link + '">' + entry.title + '</a></h2><div class="date">' + entry.date_added + '</div><div class="body">' + entry.description + '</div><div class="meta-links"><a href="' + entry.digg_link + '">Digg link</a></div></div>');

      newcount++;
    };
    ws.onclose = function() {};
  } else {
    alert("WebSockets not supported");
  }

  // menu helper
  $(".navbar-btn").click(function() {
    if ( $(".main-menu").is( ":hidden" ) ) {
      $( ".main-menu" ).slideDown( "slow" );
    } else {
      $( ".main-menu" ).slideUp("slow");
    }
  });

  $( window ).resize(function() {
    showHideMenu();
  });
});

function showHideMenu() {
  var windowWidth = $( window ).width();

  if (windowWidth >= 480) {
    $(".main-menu").show();
  }
  else {
    $(".main-menu").hide();
  }
}