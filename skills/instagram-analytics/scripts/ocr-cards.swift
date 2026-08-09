// ocr-cards.swift — текст с карточек карусели через Apple Vision. Без зависимостей.
//
// Зачем: Instagram не отдаёт текст слайдов ни через API, ни через поле `alt`
// (там «Photo by <имя> on <дата>»). Единственный способ прочитать чужую
// карусель — распознать картинки. Vision делает это на устройстве, бесплатно
// и за ~0.3 с на карточку: 10 слайдов ≈ 3 с против нескольких минут, если
// разглядывать их моделью.
//
// Запуск — через `ocr-cards.sh` (он компилирует бинарник один раз и кеширует).
// Порядок вывода = порядок аргументов, поэтому передавай слайды по возрастанию.
// Только macOS.
import Foundation
import Vision
import AppKit

let paths = Array(CommandLine.arguments.dropFirst())
guard !paths.isEmpty else {
    FileHandle.standardError.write("Использование: ocr-cards <картинка> [...]\n".data(using: .utf8)!)
    exit(2)
}

for path in paths {
    let name = (path as NSString).lastPathComponent
    guard let img = NSImage(contentsOfFile: path),
          let tiff = img.tiffRepresentation,
          let bmp = NSBitmapImageRep(data: tiff),
          let cg = bmp.cgImage else {
        print("=== \(name)")
        print("!! не открылось")
        continue
    }

    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    // Русский первым: карточки автора и большинство разведываемых аккаунтов
    // двуязычные, а порядок задаёт приоритет при неоднозначности.
    req.recognitionLanguages = ["ru-RU", "en-US"]
    req.usesLanguageCorrection = true

    do {
        try VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    } catch {
        print("=== \(name)")
        print("!! Vision не смог: \(error.localizedDescription)")
        continue
    }

    // Строки идут сверху вниз: Vision возвращает их в порядке чтения, и это
    // как раз то, что нужно для разбора роли слайда (заголовок → тело → подвал).
    let lines = (req.results ?? []).compactMap { $0.topCandidates(1).first?.string }
    print("=== \(name)")
    print(lines.joined(separator: "\n"))
}
