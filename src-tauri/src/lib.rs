use std::net::TcpListener;
use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::{Manager, State};

struct BackendProcess(Mutex<Option<Child>>);

fn is_port_available(port: u16) -> bool {
    TcpListener::bind(("127.0.0.1", port)).is_ok()
}

fn spawn_backend() -> Option<Child> {
    // Skip if port 8000 is already in use (another backend instance)
    if !is_port_available(8000) {
        println!("Port 8000 already in use — assuming backend is running externally.");
        return None;
    }

    let result = Command::new("python")
        .args(["-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"])
        .current_dir("../backend")
        .spawn();

    match result {
        Ok(child) => {
            println!("Backend started with PID: {}", child.id());
            Some(child)
        }
        Err(e) => {
            eprintln!("Failed to start backend: {}. Frontend will connect when backend is manually started.", e);
            None
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            // Spawn backend on startup
            let backend = spawn_backend();
            let state: State<BackendProcess> = app.state();
            *state.0.lock().unwrap() = backend;
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Kill backend when window closes
                let state: State<BackendProcess> = window.state();
                if let Some(mut child) = state.0.lock().unwrap().take() {
                    let _ = child.kill();
                    println!("Backend process terminated.");
                }
            }
        })
        .run(tauri::generate_context!())
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
