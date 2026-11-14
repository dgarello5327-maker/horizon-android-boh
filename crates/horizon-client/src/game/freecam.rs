//! Detached camera movement state for the game renderer.
use glam::DVec3;
use winit::keyboard::KeyCode;
#[derive(Clone, Copy, Debug, Default)]
pub(super) struct Freecam { pub enabled: bool, pub position: DVec3, pub yaw: f32, pub pitch: f32, pub speed: f64 }
impl Freecam {
 pub fn activate(&mut self, eye:DVec3, yaw:f32, pitch:f32) { self.enabled=true; self.position=eye; self.yaw=yaw; self.pitch=pitch.clamp(-89.9,89.9); if self.speed<=0.0 {self.speed=6.0;} }
 pub fn deactivate(&mut self) { self.enabled=false; }
 pub fn step_keys(&mut self, keys:&std::collections::HashSet<KeyCode>, dt:f64) {
  if !self.enabled || !dt.is_finite() || dt<=0.0 {return;}
  let down=|k| keys.contains(&k);
  let f=(if down(KeyCode::KeyW){1.0}else{0.0})-(if down(KeyCode::KeyS){1.0}else{0.0});
  let s=(if down(KeyCode::KeyD){1.0}else{0.0})-(if down(KeyCode::KeyA){1.0}else{0.0});
  let v=(if down(KeyCode::Space){1.0}else{0.0})-(if down(KeyCode::ShiftLeft){1.0}else{0.0});
  let y=f64::from(self.yaw).to_radians(); let p=f64::from(self.pitch).to_radians();
  let forward=DVec3::new(-y.sin()*p.cos(),-p.sin(),y.cos()*p.cos());
  let right=DVec3::new(y.cos(),0.0,y.sin());
  let mut m=right*s+forward*f+DVec3::Y*v;
  if m.length_squared()>1.0 {m=m.normalize();}
  let boost=if down(KeyCode::ControlLeft)||down(KeyCode::ControlRight){3.0}else{1.0};
  self.position+=m*self.speed*boost*dt;
 }
}
