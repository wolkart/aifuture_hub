// face_pitch — наклон головы (pitch, градусы) по кадрам через Apple Vision.
// usage: face_pitch <frames_dir>   → CSV в stdout: name,pitch (pitch пуст, если лица нет)
// Знак: pitch > 0 — голова опущена (смотрит вниз, например в сценарий на экране).
// Компилирует и вызывает gaze_trim.py; отдельно запускать не нужно.
import Foundation
import Vision
import CoreImage

let dir = URL(fileURLWithPath: CommandLine.arguments[1])
let files = try FileManager.default.contentsOfDirectory(atPath: dir.path)
    .filter { $0.hasSuffix(".png") }.sorted()
print("name,pitch")
for name in files {
    guard let img = CIImage(contentsOf: dir.appendingPathComponent(name)) else { continue }
    let req = VNDetectFaceRectanglesRequest()
    req.revision = VNDetectFaceRectanglesRequestRevision3  // ревизия 3 отдаёт pitch
    try VNImageRequestHandler(ciImage: img, options: [:]).perform([req])
    let face = req.results?.max(by: { $0.boundingBox.width < $1.boundingBox.width })
    let pitch = face?.pitch.map { String(format: "%.1f", $0.doubleValue * 180 / .pi) } ?? ""
    print("\(name),\(pitch)")
}
