//! Freecam movement controller core for Horizon Android / Minecraft 26.3.
//! Engine integration must feed touch/keyboard input into step() and use
//! position/yaw/pitch as the render camera without moving the player entity.

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Vec3 { pub x: f64, pub y: f64, pub z: f64 }
impl Vec3 {
    pub const ZERO: Self = Self { x: 0.0, y: 0.0, z: 0.0 };
    fn add(self, r: Self) -> Self { Self { x:self.x+r.x, y:self.y+r.y, z:self.z+r.z } }
    fn scale(self, k:f64) -> Self { Self { x:self.x*k, y:self.y*k, z:self.z*k } }
}

#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct FreecamInput {
    pub strafe:f64, pub forward:f64, pub vertical:f64,
    pub look_x:f64, pub look_y:f64, pub fast:bool,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Freecam {
    pub enabled:bool, pub position:Vec3, pub yaw:f64, pub pitch:f64,
    pub speed:f64, pub fast_multiplier:f64,
}
impl Default for Freecam {
    fn default()->Self { Self { enabled:false, position:Vec3::ZERO, yaw:0.0, pitch:0.0, speed:4.0, fast_multiplier:3.0 } }
}
impl Freecam {
    pub fn activate(&mut self, eye:Vec3, yaw:f64, pitch:f64) {
        self.position=eye; self.yaw=yaw; self.pitch=pitch.clamp(-89.9,89.9); self.enabled=true;
    }
    pub fn deactivate(&mut self) { self.enabled=false; }
    pub fn set_speed(&mut self, speed:f64) { if speed.is_finite() { self.speed=speed.clamp(0.25,32.0); } }
    /// Move the render camera for one frame; does not mutate player state.
    pub fn step(&mut self, input:FreecamInput, dt:f64) {
        if !self.enabled || !dt.is_finite() || dt<=0.0 { return; }
        self.yaw=(self.yaw+input.look_x)%360.0;
        self.pitch=(self.pitch-input.look_y).clamp(-89.9,89.9);
        let (sy,cy)=self.yaw.to_radians().sin_cos();
        let (sp,cp)=self.pitch.to_radians().sin_cos();
        let forward=Vec3{x:-sy*cp,y:-sp,z:cy*cp};
        let right=Vec3{x:cy,y:0.0,z:sy};
        let mut m=right.scale(input.strafe).add(forward.scale(input.forward)).add(Vec3{x:0.0,y:input.vertical,z:0.0});
        let len=(m.x*m.x+m.y*m.y+m.z*m.z).sqrt();
        if len>1.0 { m=m.scale(1.0/len); }
        let boost=if input.fast { self.fast_multiplier } else { 1.0 };
        self.position=self.position.add(m.scale(self.speed*boost*dt));
    }
}

#[cfg(test)] mod tests {
    use super::*;
    #[test] fn disabled_does_not_move(){let mut c=Freecam::default();c.position=Vec3{x:1.0,y:2.0,z:3.0};c.step(FreecamInput{forward:1.0,..Default::default()},1.0);assert_eq!(c.position,Vec3{x:1.0,y:2.0,z:3.0});}
    #[test] fn forward_moves_camera(){let mut c=Freecam::default();c.activate(Vec3::ZERO,0.0,0.0);c.step(FreecamInput{forward:1.0,..Default::default()},1.0);assert!((c.position.z-4.0).abs()<1e-9);}
    #[test] fn diagonal_is_normalized(){let mut c=Freecam::default();c.activate(Vec3::ZERO,0.0,0.0);c.step(FreecamInput{forward:1.0,strafe:1.0,..Default::default()},1.0);let d=(c.position.x*c.position.x+c.position.z*c.position.z).sqrt();assert!((d-4.0).abs()<1e-9);}
    #[test] fn speed_is_bounded(){let mut c=Freecam::default();c.set_speed(500.0);assert_eq!(c.speed,32.0);}
}
