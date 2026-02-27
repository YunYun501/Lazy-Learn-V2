use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::{Manager, State};

struct BackendProcess(Mutex<Option<Child>>);

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to Lazy Learn.", name)
}

fn spawn_backend() -> Option<Child> {
    // Try to spawn the Python backend
    // In development: uvicorn app.main:app --port 8000
    // In production: bundled executable (deferred to Task 28)
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
        .invoke_handler(tauri::generate_handler![greet])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
