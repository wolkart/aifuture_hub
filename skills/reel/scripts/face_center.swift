// face_center — центр самого крупного лица по кадрам (Apple Vision).
// usage: face_center <frames_dir>  → CSV в stdout: name,cx,cy (доли кадра, y сверху вниз; пусто — лица нет)
// Компилирует и вызывает face_centers.py; отдельно запускать не нужно.
import Foundation
import Vision
import CoreImage

let dir = URL(fileURLWithPath: CommandLine.arguments[1])
let files = try FileManager.default.contentsOfDirectory(atPath: dir.path)
    .filter { $0.hasSuffix(".png") }.sorted()
print("name,cx,cy")
for name in files {
    guard let img = CIImage(contentsOf: dir.appendingPathComponent(name)) else { continue }
    let req = VNDetectFaceRectanglesRequest()
    try VNImageRequestHandler(ciImage: img, options: [:]).perform([req])
    if let f = req.results?.max(by: { $0.boundingBox.width < $1.boundingBox.width }) {
        let b = f.boundingBox
        print(String(format: "%@,%.4f,%.4f", name, b.midX, 1 - b.midY))
    } else {
        print("\(name),,")
    }
}
