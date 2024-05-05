function setup() {
  const canvas = document.getElementById('canvas');
  createCanvas(innerWidth, innerHeight, P2D, canvas);
}

function draw() {
  background(color(255, 255, 255));
  circle(mouseX, mouseY, 20);
}
