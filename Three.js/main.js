import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

let camera, scene, renderer, mixer, clock;

init();
animate();

function init() {
    // 创建场景
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x263238);
    
    // 创建相机
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(2, 2, 5);
    
    // 创建渲染器
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.outputEncoding = THREE.sRGBEncoding;
    document.getElementById('container').appendChild(renderer.domElement);
    
    // 添加轨道控制器
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0.5, 0);
    controls.update();
    
    // 添加灯光
    const ambientLight = new THREE.AmbientLight(0x404040, 3);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 3);
    directionalLight.position.set(1, 1, 1).normalize();
    scene.add(directionalLight);
    
    // 初始化时钟
    clock = new THREE.Clock();
    
    // 加载模型
    const loader = new GLTFLoader();
    
    // 注意：你需要提供自己的模型文件或使用在线资源
    loader.load(
        'assets/LittlestTokyo.glb', // 替换为你的模型路径
        function (gltf) {
            const model = gltf.scene;
            model.position.set(0, 0, 0);
            model.scale.set(0.01, 0.01, 0.01);
            scene.add(model);
            
            // 创建动画混合器
            mixer = new THREE.AnimationMixer(model);
            const clips = gltf.animations;
            
            // 播放所有动画
            clips.forEach(function (clip) {
                mixer.clipAction(clip).play();
            });
        },
        undefined,
        function (error) {
            console.error('加载模型出错:', error);
        }
    );
    
    // 窗口大小调整
    window.addEventListener('resize', onWindowResize);
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
    requestAnimationFrame(animate);
    
    // 更新动画
    const delta = clock.getDelta();
    if (mixer) mixer.update(delta);
    
    renderer.render(scene, camera);
}