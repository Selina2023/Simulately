import sapien.core as sapien
from sapien.utils.viewer import Viewer
import numpy as np


class SimplePID:
    def __init__(self, kp=0.0, ki=0.0, kd=0.0):
        self.p = kp
        self.i = ki
        self.d = kd

        self._cp = 0
        self._ci = 0
        self._cd = 0

        self._last_error = 0

    def compute(self, current_error, dt):
        self._cp = current_error
        self._ci += current_error * dt
        self._cd = (current_error - self._last_error) / dt
        self._last_error = current_error
        signal = (self.p * self._cp) + \
            (self.i * self._ci) + (self.d * self._cd)
        return signal


def pid_forward(pids: list,
                target_pos: np.ndarray, 
                current_pos: np.ndarray, 
                dt: float) -> np.ndarray:
    errors = target_pos - current_pos
    qf = [pid.compute(error, dt) for pid, error in zip(pids, errors)]
    return np.array(qf)


def demo(use_internal_drive, use_external_pid):
    engine = sapien.Engine()
    renderer = sapien.VulkanRenderer()
    engine.set_renderer(renderer)

    scene_config = sapien.SceneConfig()
    scene = engine.create_scene(scene_config)
    # A small timestep for higher control accuracy
    scene.set_timestep(1 / 2000.0)
    scene.add_ground(0)


    scene.set_ambient_light([0.5, 0.5, 0.5])
    scene.add_directional_light([0, 1, -1], [0.5, 0.5, 0.5])

    viewer = Viewer(renderer)
    viewer.set_scene(scene)
    viewer.set_camera_xyz(x=-2, y=0, z=1)
    viewer.set_camera_rpy(r=0, p=-0.3, y=0)

    # Load URDF
    loader: sapien.URDFLoader = scene.create_urdf_loader()
    loader.fix_root_link = True
    robot: sapien.Articulation = loader.load("../assets/robot/panda/panda.urdf")
    robot.set_root_pose(sapien.Pose([0, 0, 0], [1, 0, 0, 0]))

    # get current qpos
    
    
    joints = robot.get_joints()
    for joint in joints:
        name = joint.name
        damping = joint.damping
        stiffness = joint.stiffness
        friction = joint.friction
        limits = joint.get_limits()
        child_link_name = joint.get_child_link().name if joint.get_child_link() is not None else None
        parent_link_name = joint.get_parent_link().name if joint.get_parent_link() is not None else None
        print(
            "name: ", name, "damping: ", damping, 
            "stiffness: ", stiffness, "friction: ", friction, 
            "limits: ", limits, "child_link_name: ", child_link_name, 
            "parent_link_name: ", parent_link_name
        )
    joint_names = [joint.name for joint in joints]
    print("joint_names: ", joint_names)
    cur_qpos = robot.get_qpos()
    print("cur_qpos: ", cur_qpos)
    
    # Set joint positions
    init_qpos = cur_qpos
    robot.set_qpos(init_qpos)
    target_qpos = [1, 1, 1, 1, 1, 1, 1, 0.04, 0.04]

    active_joints = robot.get_active_joints()
    # Or other equivalent way to get active joints
    # active_joints = [joint for joint in robot.get_joints() if joint.get_dof() > 0]

    if use_internal_drive:
        for joint_idx, joint in enumerate(active_joints):
            joint.set_drive_property(stiffness=20, damping=5)
            joint.set_drive_target(target_qpos[joint_idx])
        # Or you can directly set joint targets for an articulation
        # robot.set_drive_target(target_qpos)

    if use_external_pid:
        pids = []
        pid_parameters = [
            (40, 5, 2), (40, 5, 2), (40, 5, 2), (40, 5, 2), 
            (40, 5, 2), (40, 5, 2), (40, 5, 2), (0.1, 0, 0.02), (0.1, 0, 0.02),
        ]
        for i, joint in enumerate(active_joints):
            pids.append(SimplePID(*pid_parameters[i]))

    while not viewer.closed:
        for _ in range(4):  # render every 4 steps
            qf = robot.compute_passive_force(
                gravity=True,
                coriolis_and_centrifugal=True,
            )
            if use_external_pid:
                pid_qf = pid_forward(
                    pids,
                    target_qpos,
                    robot.get_qpos(),
                    scene.get_timestep()
                )
                qf += pid_qf
            robot.set_qf(qf)
            scene.step()
        scene.update_render()
        viewer.render()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--use-internal-drive', action='store_true')
    parser.add_argument('--use-external-pid', action='store_true')
    args = parser.parse_args()

    demo(use_internal_drive=args.use_internal_drive,
         use_external_pid=args.use_external_pid)


if __name__ == '__main__':
    main()
